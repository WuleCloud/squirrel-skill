#!/usr/bin/env python3
"""Normalize verification script."""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass

import numpy as np
import zarr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT + "/src")

from squirrel.preprocessing.Normalize import Normalize, NormalizeVerificationResult


@dataclass
class NormalizeVerifierResult:
    mean_result: NormalizeVerificationResult | None = None
    std_result: NormalizeVerificationResult | None = None
    passed: bool = False


def verify_normalization(
    original: np.ndarray,
    normalized: np.ndarray,
    mode: str = "mean",
) -> NormalizeVerificationResult:
    input_mean = float(np.mean(original))
    output_mean = float(np.mean(normalized))
    input_std = float(np.std(original))

    if mode == "mean":
        output_std = float(np.std(normalized))
        mean_ok = abs(output_mean) < 1e-6
        passed = mean_ok
        result = NormalizeVerificationResult(
            input_std=input_std,
            output_std=output_std,
            input_mean=input_mean,
            output_mean=output_mean,
            passed=passed,
        )
    else:
        output_std = float(np.std(normalized))
        mean_ok = abs(output_mean) < 1e-6
        std_ok = abs(output_std - 1.0) < 1e-1
        passed = mean_ok and std_ok
        result = NormalizeVerificationResult(
            input_std=input_std,
            output_std=output_std,
            input_mean=input_mean,
            output_mean=output_mean,
            passed=passed,
        )

    return result


class NormalizeVerifier:
    name: str = "normalize_verifier"
    description: str = "Normalize verification"

    def __init__(self, mode: str = "mean"):
        self.mode = mode

    def verify(
        self,
        input_path: str,
        normalized_path: str,
        mode: str = "mean",
    ) -> NormalizeVerifierResult:
        z_orig = zarr.open(input_path, "r")
        original = z_orig["/0/0/traces"][:]

        z_norm = zarr.open(normalized_path, "r")
        normalized = z_norm["/0/0/traces"][:]

        verify_result = verify_normalization(original, normalized, mode)

        return NormalizeVerifierResult(
            mean_result=verify_result,
            passed=verify_result.passed,
        )

    def print_result(self, result: NormalizeVerifierResult, mode: str = "mean") -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] Mode: {mode}")
        if result.mean_result:
            print(f"       Input Mean: {result.mean_result.input_mean:.6f}, Output Mean: {result.mean_result.output_mean:.6f}")
            print(f"       Input Std: {result.mean_result.input_std:.6f}, Output Std: {result.mean_result.output_std:.6f}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Normalize Verification")
    parser.add_argument("input_path", nargs="?", default="./traces/normalize_original.zarr")
    parser.add_argument("normalized_path", nargs="?", default="./result/normalize_normalized.zarr")
    parser.add_argument("--mode", default="mean", help="Normalization mode: mean or mean_stddev")
    args = parser.parse_args()

    verifier = NormalizeVerifier(mode=args.mode)
    result = verifier.verify(args.input_path, args.normalized_path, args.mode)
    verifier.print_result(result, args.mode)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "NormalizeVerifier",
    "NormalizeVerifierResult",
    "verify_normalization",
]
