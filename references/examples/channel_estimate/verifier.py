#!/usr/bin/env python3
"""Channel Estimate verification script."""

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

from squirrel.analysis.channel_estimate import ChannelEstimateAnalyzer


@dataclass
class ChannelEstimateVerificationResult:
    key_correct: bool = False
    pge_total: int = 0
    avg_pge: float = 0.0
    max_pge: int = 0
    passed: bool = False


def verify_channel_estimate(
    input_path: str,
    leakage_model: str = "sbox_output",
    pge_threshold: int = 5,
    min_bytes_threshold: float = 1.0,
) -> ChannelEstimateVerificationResult:
    z = zarr.open(input_path, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:]
    key = z[f"{tile}key"][:] if f"{tile}key" in z else None

    analyzer = ChannelEstimateAnalyzer(
        config={
            "leakage_model": leakage_model,
            "num_subkeys": 16,
            "fit_ratio": 0.8,
        }
    )

    result = analyzer.analyze(traces, plaintext=plaintext, key=key)

    key_correct = result.key_guess == list(key) if key is not None else False
    pge_total = sum(result.pge)
    avg_pge = sum(result.pge) / len(result.pge) if result.pge else 255
    max_pge = max(result.pge) if result.pge else 255

    num_bytes_below_threshold = sum(1 for p in result.pge if p < pge_threshold)
    pass_ratio = num_bytes_below_threshold / len(result.pge) if result.pge else 0
    passed = pass_ratio >= min_bytes_threshold and len(result.pge) == 16

    return ChannelEstimateVerificationResult(
        key_correct=key_correct,
        pge_total=pge_total,
        avg_pge=avg_pge,
        max_pge=max_pge,
        passed=passed,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Channel Estimate Verification")
    parser.add_argument(
        "input_path", nargs="?", default="./sim/channel_estimate/traces/ce_traces.zarr"
    )
    parser.add_argument("--leakage-model", default="sbox_output")
    parser.add_argument("--pge-threshold", type=int, default=20)
    parser.add_argument("--min-bytes-ratio", type=float, default=0.5)
    args = parser.parse_args()

    result = verify_channel_estimate(
        args.input_path, args.leakage_model, args.pge_threshold, args.min_bytes_ratio
    )

    status = "PASS" if result.passed else "FAIL"
    print(f"  [{status}] Channel Estimate Verification")
    print(f"    Key correct: {result.key_correct}")
    print(f"    PGE total: {result.pge_total}")
    print(f"    Avg PGE: {result.avg_pge:.2f}")
    print(f"    Max PGE: {result.max_pge}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
