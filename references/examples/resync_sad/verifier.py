#!/usr/bin/env python3
"""SAD alignment verification."""

import json
import sys
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import zarr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT + "/src")

from squirrel.preprocessing.Resync_SAD import SADAligner, SADVerificationResult


@dataclass
class SADVerifierResult:
    std_result: SADVerificationResult | None = None
    shift_result: dict | None = None
    passed: bool = False


def verify_alignment_variance(
    original: np.ndarray,
    aligned: np.ndarray,
    ref_trace_idx: int = 0,
) -> SADVerificationResult:
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

    return SADVerificationResult(
        std_reduction=std_reduction,
        corr_improvement=corr_improvement,
        var_reduction=var_reduction,
        shift_mae=0.0,
        passed=passed,
    )


class SADVerifier:
    name: str = "sad_verifier"

    def __init__(
        self,
        ref_trace_idx: int = 0,
        target_window: tuple[int, int] | None = None,
        max_shift: int = 50,
    ):
        self.ref_trace_idx = ref_trace_idx
        self.target_window = target_window or (500, 1500)
        self.max_shift = max_shift

    def verify(
        self,
        input_path: str,
        aligned_path: str,
        shifts_json: str | None = None,
    ) -> SADVerifierResult:
        if shifts_json is None:
            shifts_json = input_path.replace(".zarr", "_shifts.json")

        z_orig = zarr.open(input_path, "r")
        original = z_orig["/0/0/traces"][:]

        z_aligned = zarr.open(aligned_path, "r")
        aligned = z_aligned["/0/0/traces"][:]

        std_result = verify_alignment_variance(original, aligned, self.ref_trace_idx)

        shift_result = None
        if Path(shifts_json).exists():
            with open(shifts_json, "r") as f:
                shift_data = json.load(f)
            ground_truth_shifts = np.array(
                [shift_data["shifts"][str(i)] for i in range(len(original))]
            )

            aligner = SADAligner(
                config={
                    "ref_trace_idx": self.ref_trace_idx,
                    "target_window": self.target_window,
                    "max_shift": self.max_shift,
                }
            )

            aligner._calculate_ref_window(original)

            estimated_shifts = []
            for i in range(original.shape[0]):
                _, shift, _ = aligner._find_sad(original[i])
                estimated_shifts.append(shift)
            estimated_shifts = np.array(estimated_shifts)

            gt = ground_truth_shifts.copy()
            gt[self.ref_trace_idx] = 0
            mae = float(np.mean(np.abs(estimated_shifts - gt)))

            orig_peak_offsets = []
            align_peak_offsets = []
            for i in range(original.shape[0]):
                orig_peak = np.argmax(original[i]) if i != self.ref_trace_idx else np.argmax(original[i])
                align_peak = np.argmax(aligned[i]) if i != self.ref_trace_idx else np.argmax(original[i])
                ref_peak = np.argmax(original[self.ref_trace_idx])
                orig_peak_offsets.append(orig_peak - ref_peak)
                align_peak_offsets.append(align_peak - ref_peak)

            orig_peak_offsets = np.array(orig_peak_offsets)
            align_peak_offsets = np.array(align_peak_offsets)

            tolerance = 5
            accurate = 0
            for i in range(len(ground_truth_shifts)):
                if abs(align_peak_offsets[i]) <= tolerance:
                    accurate += 1
            accuracy = accurate / len(ground_truth_shifts) * 100

            shift_result = {
                "ground_truth_shifts": ground_truth_shifts,
                "estimated_shifts": estimated_shifts,
                "mae": mae,
                "passed": mae < 5.0,
                "accuracy": accuracy,
                "orig_peak_offsets": orig_peak_offsets,
                "align_peak_offsets": align_peak_offsets,
                "ref_peak_idx": np.argmax(original[self.ref_trace_idx]),
            }

        passed = std_result.passed
        if shift_result:
            passed = passed and shift_result["passed"]

        return SADVerifierResult(
            std_result=std_result,
            shift_result=shift_result,
            passed=passed,
        )

    def print_result(self, result: SADVerifierResult) -> None:
        GREEN = "\033[32m"
        RED = "\033[31m"
        RESET = "\033[0m"

        if result.std_result:
            status = f"{GREEN}PASS{RESET}" if result.std_result.passed else f"{RED}FAIL{RESET}"
            print(f"\n=== Variance Verification ===")
            print(f"  [{status}] Std Reduction: {result.std_result.std_reduction:.2f}%")
            print(f"       Corr Improvement: {result.std_result.corr_improvement:.4f}")
            print(f"       Var Reduction: {result.std_result.var_reduction:.2f}%")

        if result.shift_result:
            sr = result.shift_result
            status = f"{GREEN}PASS{RESET}" if sr["passed"] else f"{RED}FAIL{RESET}"
            print(f"\n=== Shift Verification ===")
            print(f"  [{status}] Shift MAE: {sr['mae']:.2f} samples")
            print(f"       Peak Alignment Accuracy: {sr['accuracy']:.1f}%")

            print()
            print(f"{'Trace':>6} | {'GT Shift':>8} | {'Est Shift':>10} | {'Orig Peak':>10} | {'Align Peak':>10}")
            print(f"{'':>6}   | {'':>8} | {'':>10} | {'(→/← off)':>10} | {'(→/← off)':>10}")
            print("-" * 65)

            for i in range(len(sr["ground_truth_shifts"])):
                gt = sr["ground_truth_shifts"][i]
                est = sr["estimated_shifts"][i]
                orig_off = sr["orig_peak_offsets"][i]
                align_off = sr["align_peak_offsets"][i]

                gt_str = f"→{gt}" if gt > 0 else f"←{-gt}" if gt < 0 else "0"
                est_str = f"→{est}" if est > 0 else f"←{-est}" if est < 0 else "0"
                orig_str = f"→{orig_off}" if orig_off > 0 else f"←{-orig_off}" if orig_off < 0 else "0"
                align_str = f"→{align_off}" if align_off > 0 else f"←{-align_off}" if align_off < 0 else "0"

                tolerance = 5
                ok = abs(align_off) <= tolerance
                mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"

                print(f"{i:>6} | {gt_str:>8} | {est_str:>10} | {orig_str:>10} | {align_str:>10} {mark}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAD Alignment Verification")
    parser.add_argument("input_path", nargs="?", default="./traces/sad_original.zarr")
    parser.add_argument("aligned_path", nargs="?", default="./result/sad_aligned.zarr")
    parser.add_argument("--shifts-json", default=None)
    args = parser.parse_args()

    verifier = SADVerifier()
    result = verifier.verify(args.input_path, args.aligned_path, args.shifts_json)
    verifier.print_result(result)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "SADVerifier",
    "SADVerifierResult",
    "SADVerificationResult",
    "verify_alignment_variance",
]
