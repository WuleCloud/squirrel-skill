"""Peak_Resync Alignment Verification.

Verification functions for peak-based trace alignment.
These functions contain the core verification logic, extracted from ResyncPeakDetector.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import zarr


@dataclass
class ResyncVerificationResult:
    std_reduction: float = 0.0
    corr_improvement: float = 0.0
    var_reduction: float = 0.0
    passed: bool = False


@dataclass
class ShiftVerificationResult:
    estimated_shifts: np.ndarray | None = None
    ground_truth_shifts: np.ndarray | None = None
    mae: float = 0.0
    passed: bool = False


@dataclass
class PeakVerificationResult:
    ref_peak_idx: int = 0
    ground_truth_shifts: np.ndarray | None = None
    original_peak_offsets: np.ndarray | None = None
    aligned_peak_offsets: np.ndarray | None = None
    original_offset_mean: float = 0.0
    original_offset_std: float = 0.0
    aligned_offset_mean: float = 0.0
    aligned_offset_std: float = 0.0
    alignment_accuracy_percent: float = 0.0
    passed: bool = False


@dataclass
class PeakResyncVerifierResult:
    std_result: ResyncVerificationResult | None = None
    shift_result: ShiftVerificationResult | None = None
    peak_result: PeakVerificationResult | None = None
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


def verify_alignment_shifts(
    original: np.ndarray,
    aligned: np.ndarray,
    ground_truth_shifts: np.ndarray,
    ref_trace_idx: int = 0,
    peak_type: Literal["max", "min"] = "max",
    peak_range: tuple[int, int] | None = None,
) -> ShiftVerificationResult:
    if peak_range is None:
        start, end = 0, original.shape[1]
    else:
        start, end = peak_range

    estimated_shifts = []

    for i in range(original.shape[0]):
        if peak_type == "max":
            orig_peak = np.argmax(original[i, start:end])
            align_peak = np.argmax(aligned[i, start:end])
        else:
            orig_peak = np.argmin(original[i, start:end])
            align_peak = np.argmin(aligned[i, start:end])

        shift = align_peak - orig_peak
        estimated_shifts.append(shift)

    estimated_shifts = np.array(estimated_shifts)
    gt = ground_truth_shifts.copy()
    gt[ref_trace_idx] = 0

    mae = np.mean(np.abs(estimated_shifts - gt))

    return ShiftVerificationResult(
        estimated_shifts=estimated_shifts,
        ground_truth_shifts=ground_truth_shifts,
        mae=mae,
        passed=mae < 5.0,
    )


def verify_alignment_peaks(
    original: np.ndarray,
    aligned: np.ndarray,
    ground_truth_shifts: np.ndarray | None = None,
    ref_trace_idx: int = 0,
    peak_type: Literal["max", "min"] = "max",
    peak_range: tuple[int, int] | None = None,
) -> PeakVerificationResult:
    if peak_range is None:
        start, end = 0, original.shape[1]
    else:
        start, end = peak_range

    ref_trace = original[ref_trace_idx]
    if peak_type == "max":
        ref_peak_idx = np.argmax(ref_trace[start:end])
    else:
        ref_peak_idx = np.argmin(ref_trace[start:end])

    orig_peaks = []
    align_peaks = []
    for i in range(original.shape[0]):
        if peak_type == "max":
            orig_peaks.append(np.argmax(original[i, start:end]))
            align_peaks.append(np.argmax(aligned[i, start:end]))
        else:
            orig_peaks.append(np.argmin(original[i, start:end]))
            align_peaks.append(np.argmin(aligned[i, start:end]))

    orig_peaks = np.array(orig_peaks)
    align_peaks = np.array(align_peaks)

    orig_offsets = orig_peaks - ref_peak_idx
    align_offsets = align_peaks - ref_peak_idx

    orig_offset_mean = float(np.mean(np.abs(orig_offsets)))
    orig_offset_std = float(np.std(orig_offsets))
    align_offset_mean = float(np.mean(np.abs(align_offsets)))
    align_offset_std = float(np.std(align_offsets))

    tolerance = 5
    aligned_count = np.sum(np.abs(align_offsets) <= tolerance)
    alignment_accuracy_percent = aligned_count / len(align_offsets) * 100

    passed = alignment_accuracy_percent > 90.0

    return PeakVerificationResult(
        ref_peak_idx=ref_peak_idx,
        ground_truth_shifts=ground_truth_shifts,
        original_peak_offsets=orig_offsets,
        aligned_peak_offsets=align_offsets,
        original_offset_mean=orig_offset_mean,
        original_offset_std=orig_offset_std,
        aligned_offset_mean=align_offset_mean,
        aligned_offset_std=align_offset_std,
        alignment_accuracy_percent=alignment_accuracy_percent,
        passed=passed,
    )


class PeakResyncVerifier:
    name: str = "peak_resync_verifier"
    description: str = "Peak_Resync alignment verification"

    def __init__(
        self,
        ref_trace_idx: int = 0,
        peak_type: str = "max",
        peak_range: tuple[int, int] = (400, 600),
        valid_limit: float = 0.0,
    ):
        self.ref_trace_idx = ref_trace_idx
        self.peak_type = peak_type
        self.peak_range = peak_range
        self.valid_limit = valid_limit

    def verify_std(self, original: np.ndarray, aligned: np.ndarray) -> ResyncVerificationResult:
        return verify_alignment_variance(original=original, aligned=aligned, ref_trace_idx=self.ref_trace_idx)

    def verify_shifts(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
        ground_truth_shifts: np.ndarray,
    ) -> ShiftVerificationResult:
        return verify_alignment_shifts(
            original=original,
            aligned=aligned,
            ground_truth_shifts=ground_truth_shifts,
            ref_trace_idx=self.ref_trace_idx,
            peak_type=self.peak_type,
            peak_range=self.peak_range,
        )

    def verify_peaks(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
        ground_truth_shifts: np.ndarray | None = None,
    ) -> PeakVerificationResult:
        return verify_alignment_peaks(
            original=original,
            aligned=aligned,
            ground_truth_shifts=ground_truth_shifts,
            ref_trace_idx=self.ref_trace_idx,
            peak_type=self.peak_type,
            peak_range=self.peak_range,
        )

    def verify(
        self,
        input_path: str,
        aligned_path: str,
        shifts_json: str | None = None,
    ) -> PeakResyncVerifierResult:
        if not aligned_path:
            raise ValueError(f"aligned_path is empty. input_path={input_path}")
        if shifts_json is None:
            shifts_json = input_path.replace(".zarr", "_shifts.json")

        z_orig = zarr.open(input_path, "r")
        original = z_orig["/0/0/traces"][:]

        z_aligned = zarr.open(aligned_path, "r")
        aligned = z_aligned["/0/0/traces"][:]

        std_result = self.verify_std(original, aligned)

        shifts = None
        shift_result = None
        peak_result = None

        if Path(shifts_json).exists():
            with open(shifts_json, "r") as f:
                shift_data = json.load(f)
            shifts = np.array([shift_data["shifts"][str(i)] for i in range(len(original))])
            shift_result = self.verify_shifts(original, aligned, shifts)
            peak_result = self.verify_peaks(original, aligned, shifts)
        else:
            peak_result = self.verify_peaks(original, aligned)

        passed = std_result.passed
        if shift_result:
            passed = passed and shift_result.passed
        if peak_result:
            passed = passed and peak_result.passed

        return PeakResyncVerifierResult(
            std_result=std_result,
            shift_result=shift_result,
            peak_result=peak_result,
            passed=passed,
        )

    def print_std_result(self, result: ResyncVerificationResult) -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] Variance Reduction: {result.std_reduction:.2f}%")
        print(f"       Correlation Improvement: {result.corr_improvement:.4f}")
        print(f"       Std Reduction: {result.var_reduction:.2f}%")

    def print_shift_result(self, result: ShiftVerificationResult) -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] Shift MAE: {result.mae:.2f} samples")

    def print_peak_result(self, result: PeakVerificationResult, tolerance: int = 5) -> None:
        GREEN = "\033[32m"
        RED = "\033[31m"
        RESET = "\033[0m"

        status = f"{GREEN}PASS{RESET}" if result.passed else f"{RED}FAIL{RESET}"

        print("\n=== Peak Position Verification ===\n")
        print(f"Reference peak index: {result.ref_peak_idx}")
        print(f"Peak alignment accuracy (within ±{tolerance}): [{status}]")
        print(f"   {result.alignment_accuracy_percent:.1f}% of traces have peak aligned")
        print()

        if result.ground_truth_shifts is not None:
            print(f"{'Trace':>6} | {'Shift':>8} | {'Peak Off (Orig)':>14} | {'Peak Off (Align)':>14}")
            print(f"{'':>6}   | {'':>8} | {'(→ / ← offset)':>14} | {'(→ / ← offset)':>14}")
            print("-" * 65)

            for i in range(len(result.ground_truth_shifts)):
                gt_shift = result.ground_truth_shifts[i]
                orig_off = result.original_peak_offsets[i]
                align_off = result.aligned_peak_offsets[i]

                shift_str = f"→{gt_shift}" if gt_shift > 0 else f"←{-gt_shift}" if gt_shift < 0 else "0"
                orig_str = f"→{orig_off}" if orig_off > 0 else f"←{-orig_off}" if orig_off < 0 else "0"
                align_str = f"→{align_off}" if align_off > 0 else f"←{-align_off}" if align_off < 0 else "0"

                align_ok = abs(align_off) <= tolerance
                align_mark = f"{GREEN}✓{RESET}" if align_ok else f"{RED}✗{RESET}"

                print(f"{i:>6} | {shift_str:>8} | {orig_str:>14} | {align_str:>14} {align_mark}")

            print()
            print(f"Original Traces (peak offset from reference):")
            print(f"   Mean absolute offset: {result.original_offset_mean:.1f} samples")
            print(f"   Std deviation:       {result.original_offset_std:.1f} samples")
            print()
            print(f"Aligned Traces (peak offset from reference):")
            print(f"   Mean absolute offset: {result.aligned_offset_mean:.1f} samples")
            print(f"   Std deviation:       {result.aligned_offset_std:.1f} samples")
        print()

    def print_result(self, result: PeakResyncVerifierResult) -> None:
        if result.std_result:
            self.print_std_result(result.std_result)
        if result.shift_result:
            self.print_shift_result(result.shift_result)
        if result.peak_result:
            self.print_peak_result(result.peak_result)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Peak_Resync Alignment Verification")
    parser.add_argument("input_path", nargs="?", default="./traces/peak_resync_original.zarr")
    parser.add_argument("aligned_path", nargs="?", default="./result/peak_resync_aligned.zarr")
    parser.add_argument("--shifts-json", default=None)
    args = parser.parse_args()

    verifier = PeakResyncVerifier()
    result = verifier.verify(args.input_path, args.aligned_path, args.shifts_json)
    verifier.print_result(result)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "PeakResyncVerifier",
    "PeakResyncVerifierResult",
    "ResyncVerificationResult",
    "ShiftVerificationResult",
    "PeakVerificationResult",
    "verify_alignment_variance",
    "verify_alignment_shifts",
    "verify_alignment_peaks",
]