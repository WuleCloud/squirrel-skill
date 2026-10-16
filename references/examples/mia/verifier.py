#!/usr/bin/env python3
"""MIA verification script."""

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

from squirrel.analysis.mia import MIAAnalyzer


@dataclass
class MIAVerificationResult:
    key_correct: bool = False
    num_correct: int = 0
    num_bytes: int = 16
    max_mi: float = 0.0
    avg_mi: float = 0.0
    passed: bool = False


def verify_mia(
    input_path: str,
    leakage_model: str = "hamming_weight",
    correct_threshold: int = 12,
    range_start: int = 0,
    range_end: int | None = None,
    num_subkeys: int = 16,
) -> MIAVerificationResult:
    z = zarr.open(input_path, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:] if f"{tile}plaintext" in z else None
    key = z[f"{tile}key"][:] if f"{tile}key" in z else None

    if plaintext is None:
        return MIAVerificationResult(passed=False)

    analyzer = MIAAnalyzer(
        config={
            "leakage_model": leakage_model,
            "num_subkeys": num_subkeys,
            "range_start": range_start,
            "range_end": range_end,
        }
    )

    result = analyzer.analyze(
        traces,
        plaintext=plaintext,
        key=key,
    )

    key_list = list(key) if key is not None else [0] * num_subkeys
    key_correct = (
        result.key_guess == key_list[:num_subkeys] if key is not None else False
    )
    num_correct = (
        sum(
            1
            for i, g in enumerate(result.key_guess)
            if i < len(key_list) and g == key_list[i]
        )
        if key is not None
        else 0
    )

    max_mi = 0.0
    avg_mi = 0.0
    for mi_arr in result.mutual_informations:
        if len(mi_arr) > 0:
            max_mi = max(max_mi, float(np.max(mi_arr)))
            avg_mi += float(np.mean(mi_arr))
    avg_mi /= len(result.mutual_informations) if result.mutual_informations else 1

    passed = num_correct >= correct_threshold if key is not None else False

    return MIAVerificationResult(
        key_correct=key_correct,
        num_correct=num_correct,
        num_bytes=num_subkeys,
        max_mi=max_mi,
        avg_mi=avg_mi,
        passed=passed,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MIA Verification")
    parser.add_argument(
        "input_path", nargs="?", default="./sim/mia/traces/mia_traces.zarr"
    )
    parser.add_argument("--leakage-model", default="hamming_weight")
    parser.add_argument("--correct-threshold", type=int, default=12)
    parser.add_argument("--range-start", type=int, default=0)
    parser.add_argument("--range-end", type=int, default=None)
    parser.add_argument("--num-subkeys", type=int, default=16)
    args = parser.parse_args()

    result = verify_mia(
        args.input_path,
        args.leakage_model,
        args.correct_threshold,
        args.range_start,
        args.range_end,
        args.num_subkeys,
    )

    status = "PASS" if result.passed else "FAIL"
    print(f"  [{status}] MIA Verification")
    print(f"    Key correct: {result.key_correct}")
    print(f"    Correct bytes: {result.num_correct}/{result.num_bytes}")
    print(f"    Max MI: {result.max_mi:.4f}")
    print(f"    Avg MI: {result.avg_mi:.4f}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
