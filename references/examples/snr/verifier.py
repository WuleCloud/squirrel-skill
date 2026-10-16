#!/usr/bin/env python3
"""SNR verification script."""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass

import numpy as np
import zarr

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

from squirrel.analysis.snr import SNRAnalyzer


@dataclass
class SNRVerificationResult:
    peak_snr_db: float = 0.0
    peak_sample: int = 0
    expected_snr_db: float | None = None
    snr_diff_db: float | None = None
    tolerance_db: float = 5.0
    passed: bool = False


def verify_snr(
    input_path: str,
    tolerance_db: float = 5.0,
) -> SNRVerificationResult:
    z = zarr.open(input_path, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:]

    analyzer = SNRAnalyzer(config={"threshold": 0.0})
    result = analyzer.analyze(traces, plaintext=plaintext)

    metadata_path = input_path.replace(".zarr", "_metadata.json")
    expected_snr_db = None
    snr_diff_db = None
    passed = True
    if os.path.exists(metadata_path):
        import json

        with open(metadata_path) as f:
            metadata = json.load(f)
        expected_snr_db = metadata.get("expected_snr_db")
        if expected_snr_db is not None:
            snr_diff_db = abs(result.peak_snr_db - expected_snr_db)
            passed = snr_diff_db <= tolerance_db

    return SNRVerificationResult(
        peak_snr_db=result.peak_snr_db,
        peak_sample=result.peak_sample,
        expected_snr_db=expected_snr_db,
        snr_diff_db=snr_diff_db,
        tolerance_db=tolerance_db,
        passed=passed,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SNR Verification")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="./sim/SNR/traces/snr_traces.zarr",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=5.0,
        help="Tolerance for expected SNR comparison (dB)",
    )
    args = parser.parse_args()

    result = verify_snr(args.input_path, args.tolerance)

    status = "PASS" if result.passed else "FAIL"
    print(f"  [{status}] SNR Verification")
    print(f"    Peak SNR: {result.peak_snr_db:.2f} dB at sample {result.peak_sample}")
    if result.expected_snr_db is not None:
        print(f"    Expected SNR: {result.expected_snr_db:.2f} dB")
        print(
            f"    SNR Diff: {result.snr_diff_db:.2f} dB (tolerance: {result.tolerance_db} dB)"
        )

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
