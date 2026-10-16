#!/usr/bin/env python3
"""Decimation verification script."""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass

import numpy as np
import zarr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT + "/src")

from squirrel.preprocessing.Decimation import Decimation, DecimationVerificationResult


@dataclass
class DecimationVerifierResult:
    verify_result: DecimationVerificationResult | None = None
    passed: bool = False


def verify_decimation(
    original: np.ndarray,
    decimated: np.ndarray,
    dec_factor: int = 2,
) -> DecimationVerificationResult:
    input_samples = original.shape[1]
    output_samples = decimated.shape[1]
    decimation_ratio = input_samples / output_samples

    passed = abs(decimation_ratio - dec_factor) < 0.01

    return DecimationVerificationResult(
        input_samples=input_samples,
        output_samples=output_samples,
        decimation_ratio=decimation_ratio,
        passed=passed,
    )


class DecimationVerifier:
    name: str = "decimation_verifier"
    description: str = "Decimation verification"

    def __init__(self, dec_factor: int = 2):
        self.dec_factor = dec_factor

    def verify(
        self,
        input_path: str,
        decimated_path: str,
        dec_factor: int = 2,
    ) -> DecimationVerifierResult:
        z_orig = zarr.open(input_path, "r")
        original = z_orig["/0/0/traces"][:]

        z_dec = zarr.open(decimated_path, "r")
        decimated = z_dec["/0/0/traces"][:]

        verify_result = verify_decimation(original, decimated, dec_factor)

        return DecimationVerifierResult(
            verify_result=verify_result,
            passed=verify_result.passed,
        )

    def print_result(self, result: DecimationVerifierResult, dec_factor: int = 2) -> None:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] Decimation factor: {dec_factor}")
        if result.verify_result:
            print(f"       Input samples: {result.verify_result.input_samples}")
            print(f"       Output samples: {result.verify_result.output_samples}")
            print(f"       Ratio: {result.verify_result.decimation_ratio:.2f}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Decimation Verification")
    parser.add_argument("input_path", nargs="?", default="./traces/decimation_original.zarr")
    parser.add_argument("decimated_path", nargs="?", default="./result/decimation_decimated.zarr")
    parser.add_argument("--dec-factor", type=int, default=2, help="Decimation factor")
    args = parser.parse_args()

    verifier = DecimationVerifier(dec_factor=args.dec_factor)
    result = verifier.verify(args.input_path, args.decimated_path, args.dec_factor)
    verifier.print_result(result, args.dec_factor)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "DecimationVerifier",
    "DecimationVerifierResult",
    "verify_decimation",
]
