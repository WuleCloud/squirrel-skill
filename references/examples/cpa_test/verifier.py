#!/usr/bin/env python3
"""CPA verification script."""

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

from squirrel.analysis.cpa import CPAAnalyzer


@dataclass
class CPAVerificationResult:
    key_correct: bool = False
    pge_total: int = 0
    avg_pge: float = 0.0
    max_pge: int = 0
    passed: bool = False


def verify_cpa(
    input_path: str,
    leakage_model: str = "sbox_output",
    pge_threshold: int = 10,
) -> CPAVerificationResult:
    z = zarr.open(input_path, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:]
    key = z[f"{tile}key"][:] if f"{tile}key" in z else None
    ciphertext = z[f"{tile}ciphertext"][:] if f"{tile}ciphertext" in z else None

    analyzer = CPAAnalyzer(
        config={
            "leakage_model": leakage_model,
            "num_subkeys": 16,
        }
    )

    result = analyzer.analyze(
        traces, plaintext=plaintext, ciphertext=ciphertext, key=key
    )

    key_correct = result.key_guess == list(key) if key is not None else False
    pge_total = sum(result.pge)
    avg_pge = sum(result.pge) / len(result.pge) if result.pge else 255
    max_pge = max(result.pge) if result.pge else 255
    passed = all(p < pge_threshold for p in result.pge) and len(result.pge) == 16

    return CPAVerificationResult(
        key_correct=key_correct,
        pge_total=pge_total,
        avg_pge=avg_pge,
        max_pge=max_pge,
        passed=passed,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CPA Verification")
    parser.add_argument(
        "input_path", nargs="?", default="./sim/cpa/traces/cpa_traces.zarr"
    )
    parser.add_argument("--leakage-model", default="sbox_output")
    parser.add_argument("--pge-threshold", type=int, default=10)
    args = parser.parse_args()

    result = verify_cpa(args.input_path, args.leakage_model, args.pge_threshold)

    status = "PASS" if result.passed else "FAIL"
    print(f"  [{status}] CPA Verification")
    print(f"    Key correct: {result.key_correct}")
    print(f"    PGE total: {result.pge_total}")
    print(f"    Avg PGE: {result.avg_pge:.2f}")
    print(f"    Max PGE: {result.max_pge}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
