#!/usr/bin/env python3
"""Verify Correlation Analysis results."""

from __future__ import annotations

import json
import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr

from squirrel.analysis.correlation import (
    CorrelationAnalyzer,
    CorrelationVerificationResult,
)


TILE = "/0/0/"
DEFAULT_THRESHOLD = 0.3


class CorrelationVerifier:
    name: str = "correlation_verifier"

    def __init__(
        self, data_type: str = "plaintext", threshold: float = DEFAULT_THRESHOLD
    ):
        self.data_type = data_type
        self.threshold = threshold

    def verify(self, zarr_path: str) -> CorrelationVerificationResult:
        z = zarr.open(zarr_path, "r")

        traces = z[f"{TILE}traces"][:]
        plaintext = z[f"{TILE}plaintext"][:]

        if f"{TILE}leakage_region" in z:
            leakage_region = z[f"{TILE}leakage_region"][:]
        else:
            leakage_region = np.array([400, 600, 4.0])

        analyzer = CorrelationAnalyzer(
            config={
                "data_type": self.data_type,
                "correlation_threshold": self.threshold,
            }
        )

        result = analyzer.analyze(
            traces=traces,
            plaintext=plaintext,
            input_path=zarr_path,
        )

        max_corr = abs(result.max_correlation_value)
        passed = max_corr > self.threshold

        region_start, region_end = int(leakage_region[0]), int(leakage_region[1])
        leakage_points = result.leakage_points

        return CorrelationVerificationResult(
            max_correlation=max_corr,
            threshold=self.threshold,
            passed=passed,
            metric1=max_corr,
            metric2=result.correlation_mean_abs,
        )

    def print_result(self, result: CorrelationVerificationResult) -> None:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"  [{status}] Max correlation: {result.max_correlation:.4f} (threshold: {result.threshold})"
        )


def verify(
    zarr_path: str, threshold: float = DEFAULT_THRESHOLD, data_type: str = "plaintext"
) -> bool:
    verifier = CorrelationVerifier(data_type=data_type, threshold=threshold)
    result = verifier.verify(zarr_path)

    print("")
    print("=== Correlation Verification ===")
    print(f"Data type: {data_type}")
    print(f"Threshold: >{threshold}")
    print("")

    verifier.print_result(result)

    print("")
    if result.passed:
        print("=== VERIFICATION PASS ===")
    else:
        print("=== VERIFICATION FAILED ===")

    return result.passed


def main():
    if len(sys.argv) < 2:
        print("Usage: python verifier.py <zarr_path> [threshold] [data_type]")
        sys.exit(1)

    zarr_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_THRESHOLD
    data_type = sys.argv[3] if len(sys.argv) > 3 else "plaintext"

    passed = verify(zarr_path, threshold, data_type)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
