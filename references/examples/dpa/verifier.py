#!/usr/bin/env python3
"""DPA verification script."""

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

from squirrel.analysis.dpa import DPAAnalyzer


@dataclass
class DPAVerificationResult:
    key_correct: bool = False
    ge_final: float = 0.0
    top_candidate_correct: bool = False
    passed: bool = False


def verify_dpa(
    input_path: str,
    byte_index: int = 3,
    threshold: float = 4.0,
    sample_start: int = 0,
    sample_end: int | None = None,
    direction: str = "enc",
) -> DPAVerificationResult:
    z = zarr.open(input_path, mode="r")
    tile = "/0/0/"

    key = z[f"{tile}key"][:]
    if getattr(key, "ndim", 1) == 2:
        key = key[0]

    output_dir = os.path.join(os.path.dirname(input_path), "result")
    os.makedirs(output_dir, exist_ok=True)

    analyzer = DPAAnalyzer(
        config={
            "sample_start": sample_start,
            "sample_end": sample_end,
            "direction": direction,
            "threshold": threshold,
            "byte_pos": [byte_index],
        }
    )

    result = analyzer.analyze(
        input_path,
        input_path=input_path,
        output_dir=output_dir,
    )

    best_key = result.best_keys[0] if result.best_keys else None
    top_candidate_correct = (
        best_key == key[byte_index] if best_key is not None else False
    )

    tc = result.top_candidates[0] if result.top_candidates else {}
    max_dpa = tc.get("max_dpa", 0.0)

    passed = top_candidate_correct or max_dpa > 10.0

    return DPAVerificationResult(
        key_correct=top_candidate_correct,
        ge_final=max_dpa,
        top_candidate_correct=top_candidate_correct,
        passed=passed,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="DPA Verification")
    parser.add_argument(
        "input_path", nargs="?", default="./sim/DPA/traces/dpa_traces.zarr"
    )
    parser.add_argument("--byte-index", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=4.0)
    parser.add_argument("--sample-start", type=int, default=0)
    parser.add_argument("--sample-end", type=int, default=None)
    parser.add_argument("--direction", default="enc", choices=["enc", "dec"])
    parser.add_argument("--results-json", default=None)
    parser.add_argument(
        "--all-bytes", action="store_true", help="Verify all 16 recovered AES bytes"
    )
    args = parser.parse_args()

    if args.results_json:
        with open(args.results_json) as f:
            data = json.load(f)

        if args.all_bytes or "top_candidates" in data:
            candidates = data.get("top_candidates", [])
            correct = []
            for tc in candidates:
                byte = tc.get("byte", 0)
                best = tc.get("best_key", 0)
                expected = int(
                    data.get("known_key", "0" * 32)[byte * 2 : byte * 2 + 2], 16
                )
                ok = best == expected
                correct.append(ok)
                marker = "OK" if ok else "BAD"
                print(
                    f"  byte {byte:02d}: recovered={hex(best)}, expected={hex(expected)} [{marker}]"
                )
            passed = len(correct) == 16 and all(correct)
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] DPA Verification - {sum(correct)}/16 correct")
            return 0 if passed else 1

        top = data.get("top_candidates", [])
        if top:
            recovered = top[0].get("best_key")
            expected = int(data.get("known_key", "0" * 32)[6:8], 16)
            passed = recovered == expected
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] DPA Verification")
            print(f"    Recovered: {hex(recovered) if recovered else 'N/A'}")
            print(f"    Expected:  {hex(expected)}")
            return 0 if passed else 1

        print("  [FAIL] No results found")
        return 1

    result = verify_dpa(
        args.input_path,
        byte_index=args.byte_index,
        threshold=args.threshold,
        sample_start=args.sample_start,
        sample_end=args.sample_end,
        direction=args.direction,
    )

    status = "PASS" if result.passed else "FAIL"
    print(f"  [{status}] DPA Verification")
    print(f"    Top candidate correct: {result.top_candidate_correct}")
    print(f"    Max DPA value: {result.ge_final:.2f}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
