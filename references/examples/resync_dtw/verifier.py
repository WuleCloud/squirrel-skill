"""DTW Alignment Verification."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import zarr

from squirrel.preprocessing.Resync_DTW.dtw import DTWAligner


@dataclass
class DTWVerificationResult:
    original_std: float
    aligned_std: float
    std_reduction_percent: float
    original_variance: float
    aligned_variance: float
    variance_reduction_percent: float
    original_correlation: float
    aligned_correlation: float
    passed: bool


@dataclass
class DTWPeakAlignmentResult:
    ref_trace_idx: int
    num_traces: int
    original_offsets: np.ndarray
    aligned_offsets: np.ndarray
    original_mean_offset: float
    aligned_mean_offset: float
    alignment_rate: float
    passed: bool


@dataclass
class DTWVerifierResult:
    std_result: DTWVerificationResult | None = None
    peak_result: DTWPeakAlignmentResult | None = None
    passed: bool = False


class DTWVerifier:
    name = "dtw_verifier"
    description = "DTW alignment verification for complex waveforms"

    def __init__(
        self,
        radius: int = 3,
        std_threshold: float = 50.0,
        var_threshold: float = 50.0,
        corr_threshold: float = 0.5,
        ref_trace_idx: int = 0,
    ):
        self.radius = radius
        self.std_threshold = std_threshold
        self.var_threshold = var_threshold
        self.corr_threshold = corr_threshold
        self.ref_trace_idx = ref_trace_idx
        self.aligner = DTWAligner(config={"radius": radius, "ref_trace_idx": ref_trace_idx})

    def _find_major_peaks(self, trace: np.ndarray, num_peaks: int = 5) -> np.ndarray:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(np.abs(trace), distance=len(trace)//10, prominence=0.5)
        if len(peaks) < num_peaks:
            peaks = np.argsort(np.abs(trace))[-num_peaks:]
        return np.sort(peaks)[:num_peaks]

    def _compute_std_verification(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
        ref_trace_idx: int,
    ) -> DTWVerificationResult:
        original_std = np.mean(np.std(original, axis=0))
        aligned_std = np.mean(np.std(aligned, axis=0))
        std_reduction = (original_std - aligned_std) / original_std * 100

        original_var = np.mean(np.var(original, axis=0))
        aligned_var = np.mean(np.var(aligned, axis=0))
        var_reduction = (original_var - aligned_var) / original_var * 100

        ref = aligned[ref_trace_idx]
        n_sample = min(100, len(original) - 1)
        orig_corrs = []
        align_corrs = []
        for i in range(1, n_sample + 1):
            if i < len(original):
                if np.std(original[i]) > 0 and np.std(ref) > 0:
                    orig_corrs.append(np.corrcoef(original[ref_trace_idx], original[i])[0, 1])
                if np.std(aligned[i]) > 0 and np.std(ref) > 0:
                    align_corrs.append(np.corrcoef(ref, aligned[i])[0, 1])

        orig_corr = float(np.mean(orig_corrs)) if orig_corrs else 0.0
        align_corr = float(np.mean(align_corrs)) if align_corrs else 0.0

        std_pass = std_reduction > self.std_threshold
        var_pass = var_reduction > self.var_threshold
        corr_pass = align_corr > self.corr_threshold
        all_pass = std_pass and var_pass and corr_pass

        return DTWVerificationResult(
            original_std=original_std,
            aligned_std=aligned_std,
            std_reduction_percent=std_reduction,
            original_variance=original_var,
            aligned_variance=aligned_var,
            variance_reduction_percent=var_reduction,
            original_correlation=orig_corr,
            aligned_correlation=align_corr,
            passed=all_pass,
        )

    def _compute_correlation_verification(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
        ref_trace_idx: int,
    ) -> DTWCorrelationResult:
        ref = original[ref_trace_idx]
        n_traces = len(original)

        orig_corrs = []
        align_corrs = []

        for i in range(n_traces):
            if i == ref_trace_idx:
                continue
            if np.std(original[i]) > 0 and np.std(ref) > 0:
                orig_corrs.append(np.corrcoef(ref, original[i])[0, 1])
            if np.std(aligned[i]) > 0 and np.std(ref) > 0:
                align_corrs.append(np.corrcoef(ref, aligned[i])[0, 1])

        orig_mean = float(np.mean(orig_corrs)) if orig_corrs else 0.0
        orig_std = float(np.std(orig_corrs)) if orig_corrs else 0.0
        align_mean = float(np.mean(align_corrs)) if align_corrs else 0.0
        align_std = float(np.std(align_corrs)) if align_corrs else 0.0

        improvement = align_mean - orig_mean
        passed = improvement > self.corr_threshold

        return DTWCorrelationResult(
            original_corr_mean=orig_mean,
            original_corr_std=orig_std,
            aligned_corr_mean=align_mean,
            aligned_corr_std=align_std,
            corr_improvement=improvement,
            passed=passed,
        )

    def _compute_peak_alignment_verification(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
        ref_trace_idx: int,
        tolerance: int = 5,
    ) -> DTWPeakAlignmentResult:
        ref_trace = original[ref_trace_idx]
        major_peaks = self._find_major_peaks(ref_trace, num_peaks=10)

        n_traces = len(original)

        orig_offsets = np.zeros(n_traces, dtype=np.float32)
        align_offsets = np.zeros(n_traces, dtype=np.float32)

        for i in range(n_traces):
            if i == ref_trace_idx:
                continue
            trace_peaks = self._find_major_peaks(original[i], num_peaks=10)
            align_peaks = self._find_major_peaks(aligned[i], num_peaks=10)

            offsets = []
            for rp in major_peaks:
                if len(trace_peaks) > 0:
                    closest = trace_peaks[np.argmin(np.abs(trace_peaks - rp))]
                    offsets.append(closest - rp)
            orig_offsets[i] = np.mean(np.abs(offsets)) if offsets else 0.0

            offsets = []
            for rp in major_peaks:
                if len(align_peaks) > 0:
                    closest = align_peaks[np.argmin(np.abs(align_peaks - rp))]
                    offsets.append(closest - rp)
            align_offsets[i] = np.mean(np.abs(offsets)) if offsets else 0.0

        orig_mean = float(np.mean(orig_offsets))
        align_mean = float(np.mean(align_offsets))

        accurate = np.sum(np.abs(align_offsets) <= tolerance) / (n_traces - 1) * 100

        passed = align_mean < orig_mean

        return DTWPeakAlignmentResult(
            ref_trace_idx=ref_trace_idx,
            num_traces=n_traces - 1,
            original_offsets=orig_offsets,
            aligned_offsets=align_offsets,
            original_mean_offset=orig_mean,
            aligned_mean_offset=align_mean,
            alignment_rate=accurate,
            passed=passed,
        )

    def verify_std(self, original: np.ndarray, aligned: np.ndarray) -> DTWVerificationResult:
        return self._compute_std_verification(original, aligned, self.ref_trace_idx)

    def verify_peak_alignment(
        self,
        original: np.ndarray,
        aligned: np.ndarray,
    ) -> DTWPeakAlignmentResult:
        return self._compute_peak_alignment_verification(original, aligned, self.ref_trace_idx)

    def verify(
        self,
        input_path: str,
        aligned_path: str,
        shifts_json: str | None = None,
    ) -> DTWVerifierResult:
        z_orig = zarr.open(input_path, "r")
        original = z_orig["/0/0/traces"][:]

        z_aligned = zarr.open(aligned_path, "r")
        aligned = z_aligned["/0/0/traces"][:]

        std_result = self.verify_std(original, aligned)
        peak_result = self.verify_peak_alignment(original, aligned)

        passed = std_result.passed

        return DTWVerifierResult(
            std_result=std_result,
            peak_result=peak_result,
            passed=passed,
        )

    def _print_std_result(self, result: DTWVerificationResult) -> None:
        GREEN = "\033[32m"
        RED = "\033[31m"
        RESET = "\033[0m"

        std_pass = result.std_reduction_percent > self.std_threshold
        var_pass = result.variance_reduction_percent > self.var_threshold
        corr_pass = result.aligned_correlation > self.corr_threshold

        print("\n=== DTW Alignment Verification (Statistics) ===\n")

        std_status = f"{GREEN}PASS{RESET}" if std_pass else f"{RED}FAIL{RESET}"
        print(f"1. Standard Deviation: [{std_status}]")
        print(f"   Original: {result.original_std:.4f}")
        print(f"   Aligned:  {result.aligned_std:.4f}")
        print(f"   Reduction: {result.std_reduction_percent:.1f}% (threshold: >{self.std_threshold}%)")
        print()

        var_status = f"{GREEN}PASS{RESET}" if var_pass else f"{RED}FAIL{RESET}"
        print(f"2. Variance: [{var_status}]")
        print(f"   Original: {result.original_variance:.4f}")
        print(f"   Aligned:  {result.aligned_variance:.4f}")
        print(f"   Reduction: {result.variance_reduction_percent:.1f}% (threshold: >{self.var_threshold}%)")
        print()

        corr_status = f"{GREEN}PASS{RESET}" if corr_pass else f"{RED}FAIL{RESET}"
        print(f"3. Correlation: [{corr_status}]")
        print(f"   Original: {result.original_correlation:.4f}")
        print(f"   Aligned:  {result.aligned_correlation:.4f}")
        print(f"   Threshold: >{self.corr_threshold}")
        print()

        overall_status = f"{GREEN}PASS{RESET}" if result.passed else f"{RED}FAIL{RESET}"
        print(f"=== Overall Result: [{overall_status}] ===")
        print()

    def _print_peak_result(self, result: DTWPeakAlignmentResult, tolerance: int = 5) -> None:
        GREEN = "\033[32m"
        RED = "\033[31m"
        RESET = "\033[0m"

        status = f"{GREEN}PASS{RESET}" if result.passed else f"{RED}FAIL{RESET}"

        print("\n=== Major Peak Alignment Verification ===\n")
        print(f"Reference trace index: {result.ref_trace_idx}")
        print(f"Traces verified: {result.num_traces}")
        print(f"Major Peaks Alignment: [{status}]")
        print(f"   {result.alignment_rate:.1f}% of traces aligned (within ±{tolerance})")
        print()
        print(f"Mean Peak Offset from Reference:")
        print(f"   Original: {result.original_mean_offset:.2f} samples")
        print(f"   Aligned:  {result.aligned_mean_offset:.2f} samples")
        reduction = (1 - result.aligned_mean_offset / result.original_mean_offset) * 100 if result.original_mean_offset > 0 else 0
        print(f"   Reduction: {reduction:.1f}%")
        print()

    def print_result(self, dtw_result: DTWVerifierResult) -> None:
        if dtw_result.std_result:
            self._print_std_result(dtw_result.std_result)
        if dtw_result.peak_result:
            self._print_peak_result(dtw_result.peak_result)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "./traces/dtw_original.zarr"
    aligned_path = sys.argv[2] if len(sys.argv) > 2 else "./result/dtw_aligned.zarr"
    radius = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    verifier = DTWVerifier(radius=radius)
    result = verifier.verify(input_path, aligned_path)
    verifier.print_result(result)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())