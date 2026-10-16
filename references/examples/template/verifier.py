#!/usr/bin/env python3
"""Template Attack verification script."""

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


@dataclass
class TemplateVerificationResult:
    key_correct: bool = False
    top_candidate_correct: bool = False
    passed: bool = False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Template Attack Verification")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="./sim/TemplateAttack/traces/template_traces.zarr",
    )
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
            passed = len(candidates) == 16 and all(correct)
            status = "PASS" if passed else "FAIL"
            print(
                f"  [{status}] Template Attack Verification - {sum(correct)}/16 correct"
            )
            return 0 if passed else 1

        print("  [FAIL] No results found")
        return 1

    print("  [FAIL] No results JSON provided")
    return 1


if __name__ == "__main__":
    sys.exit(main())
