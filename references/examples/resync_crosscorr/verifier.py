from __future__ import annotations

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr
import scipy as sp

from squirrel.preprocessing.Resync_CrossCorr import ResyncCrossCorrAligner, CrossCorrVerificationResult


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def verify_alignment(original: np.ndarray, aligned: np.ndarray, ref_trace_idx: int = 0) -> CrossCorrVerificationResult:
    ref_trace = aligned[ref_trace_idx]

    orig_std = np.std(original)
    aligned_std = np.std(aligned)
    std_reduction = (orig_std - aligned_std) / orig_std * 100 if orig_std > 0 else 0

    orig_corrs = []
    aligned_corrs = []
    for i in range(original.shape[0]):
        if i != ref_trace_idx:
            orig_corrs.append(np.corrcoef(original[i], original[ref_trace_idx])[0, 1])
            aligned_corrs.append(np.corrcoef(aligned[i], ref_trace)[0, 1])
    orig_corr = np.mean(orig_corrs) if orig_corrs else 0
    aligned_corr = np.mean(aligned_corrs) if aligned_corrs else 0
    corr_improvement = aligned_corr - orig_corr

    orig_var = np.var(original)
    aligned_var = np.var(aligned)
    var_reduction = (orig_var - aligned_var) / orig_var * 100 if orig_var > 0 else 0

    passed = corr_improvement > 0.1

    return CrossCorrVerificationResult(
        std_reduction=std_reduction,
        corr_improvement=corr_improvement,
        var_reduction=var_reduction,
        passed=passed,
    )


def verify_crosscorr_shifts(
    original: np.ndarray,
    aligned: np.ndarray,
    ground_truth_shifts: np.ndarray,
    ref_trace_idx: int = 0,
    window: tuple[int, int] | None = None,
) -> dict:
    if window is None:
        window = (450, 550)

    ref_trace = original[ref_trace_idx]
    ref_window = ref_trace[window[0]:window[1]]
    ref_window_reversed = ref_window[::-1]

    orig_offsets = []
    align_offsets = []

    for i in range(original.shape[0]):
        cross_orig = sp.signal.correlate(original[i], ref_window_reversed, mode="valid")
        cross_align = sp.signal.correlate(aligned[i], ref_window_reversed, mode="valid")

        orig_peak = np.argmax(cross_orig)
        align_peak = np.argmax(cross_align)

        orig_offsets.append(orig_peak)
        align_offsets.append(align_peak)

    orig_offsets = np.array(orig_offsets)
    align_offsets = np.array(align_offsets)

    orig_offset_mean = float(np.mean(np.abs(orig_offsets - orig_offsets[ref_trace_idx])))
    orig_offset_std = float(np.std(orig_offsets - orig_offsets[ref_trace_idx]))
    align_offset_mean = float(np.mean(np.abs(align_offsets - align_offsets[ref_trace_idx])))
    align_offset_std = float(np.std(align_offsets - align_offsets[ref_trace_idx]))

    gt = ground_truth_shifts.copy()
    gt[ref_trace_idx] = 0

    orig_offsets_shifted = orig_offsets - orig_offsets[ref_trace_idx]
    align_offsets_shifted = align_offsets - align_offsets[ref_trace_idx]

    orig_mae = np.mean(np.abs(orig_offsets_shifted))
    align_mae = np.mean(np.abs(align_offsets_shifted))

    tolerance = 5
    aligned_count = np.sum(np.abs(align_offsets_shifted) <= tolerance)
    alignment_accuracy_percent = aligned_count / len(gt) * 100

    passed = alignment_accuracy_percent > 80.0

    return {
        "ref_peak_idx": int(np.argmax(sp.signal.correlate(ref_trace, ref_window, mode="valid"))),
        "ground_truth_shifts": gt,
        "original_offsets": orig_offsets_shifted,
        "aligned_offsets": align_offsets_shifted,
        "original_offset_mean": orig_offset_mean,
        "original_offset_std": orig_offset_std,
        "aligned_offset_mean": align_offset_mean,
        "aligned_offset_std": align_offset_std,
        "original_mae": float(orig_mae),
        "aligned_mae": float(align_mae),
        "alignment_accuracy_percent": alignment_accuracy_percent,
        "passed": passed,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Verify CrossCorr alignment")
    parser.add_argument("input_path", nargs="?", default="./sim/preprocessing/Resync_CrossCorr/traces/crosscorr_original.zarr")
    parser.add_argument("aligned_path", nargs="?", default="./sim/preprocessing/Resync_CrossCorr/result/crosscorr_aligned.zarr")
    parser.add_argument("--ref-trace-idx", type=int, default=0)
    parser.add_argument("--window-start", type=int, default=450)
    parser.add_argument("--window-end", type=int, default=550)
    args = parser.parse_args()

    window = (args.window_start, args.window_end)

    z_orig = zarr.open(args.input_path, "r")
    original = z_orig["/0/0/traces"][:]
    shifts = z_orig["/0/0/shifts"][:] if "/0/0/shifts" in z_orig else None

    z_aligned = zarr.open(args.aligned_path, "r")
    aligned = z_aligned["/0/0/traces"][:]

    print(f"Original traces: {original.shape}")
    print(f"Aligned traces: {aligned.shape}")

    result = verify_alignment(original, aligned, args.ref_trace_idx)

    status = "PASS" if result.passed else "FAIL"
    print(f"\n  [{status}] Correlation Improvement: {result.corr_improvement:.4f}")
    print(f"       Spread Reduction: {result.std_reduction:.2f}%")

    if shifts is not None:
        print(f"\n=== Cross-Correlation Shift Verification ===\n")
        shift_result = verify_crosscorr_shifts(original, aligned, shifts, args.ref_trace_idx, window)

        print(f"Original MAE: {shift_result['original_mae']:.2f} samples")
        print(f"Aligned MAE: {shift_result['aligned_mae']:.2f} samples")
        print(f"Alignment accuracy (within ±5): {shift_result['alignment_accuracy_percent']:.1f}%")

        print()
        print(f"{'Trace':>6} | {'GT Shift':>10} | {'Orig Offset':>12} | {'Align Offset':>12}")
        print(f"{'':>6} | {'':>10} | {'':>12} | {'':>12}")
        print("-" * 55)

        for i in range(len(shifts)):
            gt_shift = shift_result['ground_truth_shifts'][i]
            orig_off = shift_result['original_offsets'][i]
            align_off = shift_result['aligned_offsets'][i]

            gt_str = f"→{gt_shift}" if gt_shift > 0 else f"←{-gt_shift}" if gt_shift < 0 else "0"
            orig_str = f"→{int(orig_off)}" if orig_off > 0 else f"←{-int(orig_off)}" if orig_off < 0 else "0"
            align_str = f"→{int(align_off)}" if align_off > 0 else f"←{-int(align_off)}" if align_off < 0 else "0"

            tolerance = 5
            align_ok = abs(align_off) <= tolerance
            align_mark = f"{GREEN}✓{RESET}" if align_ok else f"{RED}✗{RESET}"

            print(f"{i:>6} | {gt_str:>10} | {orig_str:>12} | {align_str:>12} {align_mark}")

        print()
        print(f"Original Traces (offset from reference):")
        print(f"   Mean absolute offset: {shift_result['original_offset_mean']:.1f} samples")
        print(f"   Std deviation:        {shift_result['original_offset_std']:.1f} samples")
        print()
        print(f"Aligned Traces (offset from reference):")
        print(f"   Mean absolute offset: {shift_result['aligned_offset_mean']:.1f} samples")
        print(f"   Std deviation:        {shift_result['aligned_offset_std']:.1f} samples")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())