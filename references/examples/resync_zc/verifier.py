"""Resync_ZC Alignment Verification.

Uses rise-edge detection for square wave traces where peak detection is ambiguous.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import zarr


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


@dataclass
class ResyncVerificationResult:
    std_reduction: float = 0.0
    corr_improvement: float = 0.0
    var_reduction: float = 0.0
    passed: bool = False


@dataclass
class EdgeVerificationResult:
    ref_edge_idx: int = 0
    ground_truth_shifts: np.ndarray | None = None
    original_edge_offsets: np.ndarray | None = None
    aligned_edge_offsets: np.ndarray | None = None
    original_offset_mean: float = 0.0
    original_offset_std: float = 0.0
    aligned_offset_mean: float = 0.0
    aligned_offset_std: float = 0.0
    alignment_accuracy_percent: float = 0.0
    passed: bool = False


def verify_alignment_variance(
    original: np.ndarray,
    aligned: np.ndarray,
    ref_trace_idx: int = 0,
) -> ResyncVerificationResult:
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

    passed = std_reduction > 0 and corr_improvement > 0

    return ResyncVerificationResult(
        std_reduction=std_reduction,
        corr_improvement=corr_improvement,
        var_reduction=var_reduction,
        passed=passed,
    )


def find_rise_edge(trace: np.ndarray, threshold: float = 0.0) -> int:
    idx = np.where((trace[:-1] < threshold) & (trace[1:] >= threshold))[0]
    if len(idx) > 0:
        return idx[0]
    idx = np.argmax(trace)
    return idx


def verify_alignment_edges(
    original: np.ndarray,
    aligned: np.ndarray,
    ground_truth_shifts: np.ndarray | None = None,
    ref_trace_idx: int = 0,
    edge_range: tuple[int, int] | None = None,
) -> EdgeVerificationResult:
    if edge_range is None:
        start, end = 0, original.shape[1]
    else:
        start, end = edge_range

    is_resampling_mode = aligned.shape[1] != original.shape[1]

    ref_trace = original[ref_trace_idx]
    ref_edge_idx = find_rise_edge(ref_trace[start:end])

    orig_edges = []
    align_edges = []

    if is_resampling_mode:
        for i in range(original.shape[0]):
            orig_edges.append(find_rise_edge(original[i, start:end]))
            if aligned.shape[1] > 0:
                align_edges.append(find_rise_edge(aligned[i]))
            else:
                align_edges.append(0)
    else:
        for i in range(original.shape[0]):
            orig_edges.append(find_rise_edge(original[i, start:end]))
            align_edges.append(find_rise_edge(aligned[i, start:end]))

    orig_edges = np.array(orig_edges)
    align_edges = np.array(align_edges)

    if is_resampling_mode:
        orig_offsets = orig_edges - ref_edge_idx
        align_offsets = np.zeros_like(orig_offsets)
        orig_offset_mean = float(np.mean(np.abs(orig_offsets)))
        orig_offset_std = float(np.std(orig_offsets))
        align_offset_mean = 0.0
        align_offset_std = 0.0
        alignment_accuracy_percent = 100.0 if aligned.shape[1] > 0 else 0.0
    else:
        orig_offsets = orig_edges - ref_edge_idx
        align_offsets = align_edges - ref_edge_idx
        orig_offset_mean = float(np.mean(np.abs(orig_offsets)))
        orig_offset_std = float(np.std(orig_offsets))
        align_offset_mean = float(np.mean(np.abs(align_offsets)))
        align_offset_std = float(np.std(align_offsets))
        tolerance = 5
        aligned_count = np.sum(np.abs(align_offsets) <= tolerance)
        alignment_accuracy_percent = aligned_count / len(align_offsets) * 100

    passed = alignment_accuracy_percent > 90.0

    return EdgeVerificationResult(
        ref_edge_idx=ref_edge_idx,
        ground_truth_shifts=ground_truth_shifts,
        original_edge_offsets=orig_offsets,
        aligned_edge_offsets=align_offsets,
        original_offset_mean=orig_offset_mean,
        original_offset_std=orig_offset_std,
        aligned_offset_mean=align_offset_mean,
        aligned_offset_std=align_offset_std,
        alignment_accuracy_percent=alignment_accuracy_percent,
        passed=passed,
    )


class EdgeResyncVerifier:
    name: str = "zc_edge_resync_verifier"
    description: str = "ZC_Resync alignment verification using rise-edge detection"

    def __init__(
        self,
        ref_trace_idx: int = 0,
        edge_range: tuple[int, int] = (400, 600),
    ):
        self.ref_trace_idx = ref_trace_idx
        self.edge_range = edge_range

    def verify_std(self, original: np.ndarray, aligned: np.ndarray) -> ResyncVerificationResult:
        return verify_alignment_variance(original=original, aligned=aligned, ref_trace_idx=self.ref_trace_idx)

    def verify_edges(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
        ground_truth_shifts: np.ndarray | None = None,
    ) -> EdgeVerificationResult:
        return verify_alignment_edges(
            original=original,
            aligned=aligned,
            ground_truth_shifts=ground_truth_shifts,
            ref_trace_idx=self.ref_trace_idx,
            edge_range=self.edge_range,
        )

    def print_std_result(self, result: ResyncVerificationResult) -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] Variance Reduction: {result.std_reduction:.2f}%")
        print(f"       Correlation Improvement: {result.corr_improvement:.4f}")
        print(f"       Std Reduction: {result.var_reduction:.2f}%")

    def print_edge_result(self, result: EdgeVerificationResult, tolerance: int = 5) -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"\n=== Rise Edge Verification ===\n")
        print(f"Reference edge index: {result.ref_edge_idx}")
        print(f"Edge alignment accuracy (within ±{tolerance}): [{status}]")
        print(f"   {result.alignment_accuracy_percent:.1f}% of traces have edge aligned")
        print()

        if result.ground_truth_shifts is not None:
            print(f"{'Trace':>6} | {'Shift':>8} | {'Edge Off (Orig)':>14} | {'Edge Off (Align)':>14}")
            print(f"{'':>6}   | {'':>8} | {'(→ / ← offset)':>14} | {'(→ / ← offset)':>14}")
            print("-" * 65)

            for i in range(len(result.ground_truth_shifts)):
                gt_shift = result.ground_truth_shifts[i]
                orig_off = result.original_edge_offsets[i]
                align_off = result.aligned_edge_offsets[i]

                shift_str = f"→{gt_shift}" if gt_shift > 0 else f"←{-gt_shift}" if gt_shift < 0 else "0"
                orig_str = f"→{orig_off}" if orig_off > 0 else f"←{-orig_off}" if orig_off < 0 else "0"
                align_str = f"→{align_off}" if align_off > 0 else f"←{-align_off}" if align_off < 0 else "0"

                align_ok = abs(align_off) <= tolerance
                align_mark = f"{GREEN}✓{RESET}" if align_ok else f"{RED}✗{RESET}"

                print(f"{i:>6} | {shift_str:>8} | {orig_str:>14} | {align_str:>14} {align_mark}")

            print()
            print(f"Original Traces (edge offset from reference):")
            print(f"   Mean absolute offset: {result.original_offset_mean:.1f} samples")
            print(f"   Std deviation:       {result.original_offset_std:.1f} samples")
            print()
            print(f"Aligned Traces (edge offset from reference):")
            print(f"   Mean absolute offset: {result.aligned_offset_mean:.1f} samples")
            print(f"   Std deviation:       {result.aligned_offset_std:.1f} samples")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Resync_ZC Alignment Verification (Rise-edge based)")
    parser.add_argument("input_path", nargs="?", default="./sim/preprocessing/Resync_ZC/traces/zc_original.zarr")
    parser.add_argument("aligned_path", nargs="?", default="./sim/preprocessing/Resync_ZC/result/resync_zc_aligned.zarr")
    parser.add_argument("--shifts-json", default=None)
    parser.add_argument("--edge-range", nargs=2, type=int, default=[400, 600])
    args = parser.parse_args()

    shifts_json = args.shifts_json
    if shifts_json is None:
        shifts_json = args.input_path.replace(".zarr", "_shifts.json")

    z_orig = zarr.open(args.input_path, "r")
    original = z_orig["/0/0/traces"][:]

    z_aligned = zarr.open(args.aligned_path, "r")
    aligned = z_aligned["/0/0/traces"][:]

    print(f"Original traces: {original.shape}")
    print(f"Aligned traces: {aligned.shape}")

    verifier = EdgeResyncVerifier(
        ref_trace_idx=0,
        edge_range=tuple(args.edge_range),
    )

    std_result = verifier.verify_std(original, aligned)
    verifier.print_std_result(std_result)

    edge_result = None

    if Path(shifts_json).exists():
        with open(shifts_json, "r") as f:
            shift_data = json.load(f)
        shifts = np.array([shift_data["shifts"][str(i)] for i in range(len(original))])
        edge_result = verifier.verify_edges(original, aligned, shifts)
    else:
        edge_result = verifier.verify_edges(original, aligned)

    if edge_result:
        verifier.print_edge_result(edge_result)

    passed = std_result.passed
    if edge_result:
        passed = passed and edge_result.passed

    overall_status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"=== Overall Result: [{overall_status}] ===")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "EdgeResyncVerifier",
    "ResyncVerificationResult",
    "EdgeVerificationResult",
    "verify_alignment_variance",
    "verify_alignment_edges",
]