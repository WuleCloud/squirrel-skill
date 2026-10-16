#!/usr/bin/env python3
"""MixColumns CPA verification script."""

from __future__ import annotations

import json
import sys
import os
from dataclasses import dataclass

import numpy as np
import zarr

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

from squirrel.analysis.mix_columns import MixColumnsCPAAnalyzer


@dataclass
class MixColumnsVerificationResult:
    key_correct: bool = False
    pge_total: int = 0
    avg_pge: float = 0.0
    max_pge: int = 0
    pge_zero_count: int = 0
    success_rate: float = 0.0
    passed: bool = False


def verify_mix_columns_cpa(
    input_path: str,
    vec_type: str = "column",
    pge_threshold: int = 10,
) -> MixColumnsVerificationResult:
    z = zarr.open(input_path, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:]
    key = z[f"{tile}key"][:] if f"{tile}key" in z else None

    analyzer = MixColumnsCPAAnalyzer(
        config={
            "vec_type": vec_type,
            "hamming_distance": True,
        }
    )

    result = analyzer.analyze(traces, plaintext=plaintext, key=key)

    key_correct = result.key_guess == list(key) if key is not None else False
    pge_total = sum(result.pge)
    avg_pge = sum(result.pge) / len(result.pge) if result.pge else 255
    max_pge = max(result.pge) if result.pge else 255
    pge_zero_count = sum(1 for p in result.pge if p == 0)
    success_rate = (pge_zero_count / 16) * 100.0 if result.pge else 0.0
    passed = success_rate >= 80.0 and len(result.pge) == 16

    return MixColumnsVerificationResult(
        key_correct=key_correct,
        pge_total=pge_total,
        avg_pge=avg_pge,
        max_pge=max_pge,
        pge_zero_count=pge_zero_count,
        success_rate=success_rate,
        passed=passed,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MixColumns CPA Verification")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="./sim/mix_columns/traces/mix_columns_traces.zarr",
    )
    parser.add_argument("--vec-type", default="column", choices=["column", "row"])
    parser.add_argument("--pge-threshold", type=int, default=10)
    parser.add_argument("--success-rate-threshold", type=float, default=80.0)
    args = parser.parse_args()

    result = verify_mix_columns_cpa(args.input_path, args.vec_type, args.pge_threshold)

    status = "PASS" if result.passed else "FAIL"
    print(f"  [{status}] MixColumns CPA Verification")
    print(f"    Key correct: {result.key_correct}")
    print(f"    PGE = 0 for {result.pge_zero_count}/16 bytes")
    print(f"    Success rate: {result.success_rate:.1f}%")
    print(f"    PGE total: {result.pge_total}")
    print(f"    Avg PGE: {result.avg_pge:.2f}")
    print(f"    Max PGE: {result.max_pge}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
