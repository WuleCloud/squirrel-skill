"""Digital Filter Verification.

Verification functions for digital filter preprocessing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
import zarr


@dataclass
class FilterVerifierResult:
    std_result: FilterVerificationResult | None = None
    freq_result: FrequencyVerificationResult | None = None
    passed: bool = False


@dataclass
class FilterVerificationResult:
    input_std: float = 0.0
    output_std: float = 0.0
    std_reduction_percent: float = 0.0
    input_power: float = 0.0
    output_power: float = 0.0
    power_reduction_percent: float = 0.0
    passed: bool = False


@dataclass
class FrequencyVerificationResult:
    low_freq_energy_before: float = 0.0
    low_freq_energy_after: float = 0.0
    low_freq_reduction_percent: float = 0.0
    mid_freq_energy_before: float = 0.0
    mid_freq_energy_after: float = 0.0
    mid_freq_reduction_percent: float = 0.0
    high_freq_energy_before: float = 0.0
    high_freq_energy_after: float = 0.0
    high_freq_reduction_percent: float = 0.0
    freq_threshold: float = 0.1
    freq2_threshold: float = 0.25
    passed: bool = False


def verify_filtering(
    original: np.ndarray,
    filtered: np.ndarray,
) -> FilterVerificationResult:
    input_std = float(np.std(original))
    output_std = float(np.std(filtered))
    std_reduction = (input_std - output_std) / input_std * 100 if input_std > 0 else 0

    input_power = float(np.mean(original**2))
    output_power = float(np.mean(filtered**2))
    power_reduction = (input_power - output_power) / input_power * 100 if input_power > 0 else 0

    passed = std_reduction > 0 or power_reduction > 0

    return FilterVerificationResult(
        input_std=input_std,
        output_std=output_std,
        std_reduction_percent=std_reduction,
        input_power=input_power,
        output_power=output_power,
        power_reduction_percent=power_reduction,
        passed=passed,
    )


def verify_frequency_content(
    original: np.ndarray,
    filtered: np.ndarray,
    freq_threshold: float = 0.1,
    freq2_threshold: float = 0.25,
) -> FrequencyVerificationResult:
    avg_orig = np.mean(original, axis=0)
    avg_filt = np.mean(filtered, axis=0)

    n_samples = avg_orig.shape[0]
    freqs = np.fft.rfftfreq(n_samples)
    spectrum_orig = np.abs(np.fft.rfft(avg_orig))
    spectrum_filt = np.abs(np.fft.rfft(avg_filt))

    low_mask = freqs < freq_threshold
    mid_mask = (freqs >= freq_threshold) & (freqs < freq2_threshold)
    high_mask = freqs >= freq2_threshold

    low_energy_orig = float(np.sum(spectrum_orig[low_mask] ** 2))
    low_energy_filt = float(np.sum(spectrum_filt[low_mask] ** 2))
    mid_energy_orig = float(np.sum(spectrum_orig[mid_mask] ** 2))
    mid_energy_filt = float(np.sum(spectrum_filt[mid_mask] ** 2))
    high_energy_orig = float(np.sum(spectrum_orig[high_mask] ** 2))
    high_energy_filt = float(np.sum(spectrum_filt[high_mask] ** 2))

    low_reduction = (low_energy_orig - low_energy_filt) / low_energy_orig * 100 if low_energy_orig > 0 else 0
    mid_reduction = (mid_energy_orig - mid_energy_filt) / mid_energy_orig * 100 if mid_energy_orig > 0 else 0
    high_reduction = (high_energy_orig - high_energy_filt) / high_energy_orig * 100 if high_energy_orig > 0 else 0

    return FrequencyVerificationResult(
        low_freq_energy_before=low_energy_orig,
        low_freq_energy_after=low_energy_filt,
        low_freq_reduction_percent=low_reduction,
        mid_freq_energy_before=mid_energy_orig,
        mid_freq_energy_after=mid_energy_filt,
        mid_freq_reduction_percent=mid_reduction,
        high_freq_energy_before=high_energy_orig,
        high_freq_energy_after=high_energy_filt,
        high_freq_reduction_percent=high_reduction,
        freq_threshold=freq_threshold,
        freq2_threshold=freq2_threshold,
        passed=True,
    )


class FilterVerifier:
    name: str = "digital_filter_verifier"
    description: str = "Digital filter verification"

    def verify(
        self,
        input_path: str,
        filtered_path: str,
        filter_type: str = "low",
        freq_threshold: float = 0.1,
        freq2_threshold: float = 0.25,
    ) -> FilterVerifierResult:
        z_orig = zarr.open(input_path, "r")
        original = z_orig["/0/0/traces"][:]

        z_filtered = zarr.open(filtered_path, "r")
        filtered = z_filtered["/0/0/traces"][:]

        std_result = verify_filtering(original, filtered)
        freq_result = verify_frequency_content(original, filtered, freq_threshold, freq2_threshold)

        if filter_type == "high":
            low_ok = freq_result.low_freq_reduction_percent > 90
            high_ok = freq_result.high_freq_reduction_percent < 50
            passed = low_ok and high_ok
            freq_result.passed = passed
        elif filter_type == "low":
            high_ok = freq_result.high_freq_reduction_percent > 90
            low_ok = freq_result.low_freq_reduction_percent < 50
            passed = high_ok and low_ok
            freq_result.passed = passed
        elif filter_type == "bandpass":
            low_ok = freq_result.low_freq_reduction_percent > 90
            mid_ok = abs(freq_result.mid_freq_reduction_percent) < 50
            high_ok = freq_result.high_freq_reduction_percent > 90
            passed = low_ok and mid_ok and high_ok
            freq_result.passed = passed
        elif filter_type == "bandstop":
            low_ok = abs(freq_result.low_freq_reduction_percent) < 50
            mid_ok = freq_result.mid_freq_reduction_percent > 90
            high_ok = abs(freq_result.high_freq_reduction_percent) < 50
            passed = low_ok and mid_ok and high_ok
            freq_result.passed = passed
        else:
            passed = std_result.passed

        return FilterVerifierResult(
            std_result=std_result,
            freq_result=freq_result,
            passed=passed,
        )

    def print_result(self, result: FilterVerifierResult, filter_type: str = "low") -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] Std Reduction: {result.std_result.std_reduction_percent:.2f}%")
        print(f"       Power Reduction: {result.std_result.power_reduction_percent:.2f}%")
        if result.freq_result:
            print(f"       Freq [0-{result.freq_result.freq_threshold:.2f}] Reduction: {result.freq_result.low_freq_reduction_percent:.2f}%")
            print(f"       Freq [{result.freq_result.freq_threshold:.2f}-{result.freq_result.freq2_threshold:.2f}] Reduction: {result.freq_result.mid_freq_reduction_percent:.2f}%")
            print(f"       Freq [{result.freq_result.freq2_threshold:.2f}-0.5] Reduction: {result.freq_result.high_freq_reduction_percent:.2f}%")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Digital Filter Verification")
    parser.add_argument("input_path", nargs="?", default="./traces/digital_filter_original.zarr")
    parser.add_argument("filtered_path", nargs="?", default="./result/digital_filtered.zarr")
    parser.add_argument("--filter-type", default="low", help="Filter type: low, high, bandpass, bandstop")
    parser.add_argument("--freq-threshold", type=float, default=0.1, help="First frequency threshold")
    parser.add_argument("--freq2-threshold", type=float, default=0.25, help="Second frequency threshold (for bandpass/bandstop)")
    args = parser.parse_args()

    verifier = FilterVerifier()
    result = verifier.verify(args.input_path, args.filtered_path, args.filter_type, args.freq_threshold, args.freq2_threshold)
    verifier.print_result(result, args.filter_type)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "FilterVerifier",
    "FilterVerifierResult",
    "FilterVerificationResult",
    "FrequencyVerificationResult",
    "verify_filtering",
    "verify_frequency_content",
]
