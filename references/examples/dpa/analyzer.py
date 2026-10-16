#!/usr/bin/env python3
"""DPA analyzer script."""

import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import json
import numpy as np
import zarr

from squirrel.analysis.dpa import DPAAnalyzer


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="DPA Attack Analyzer")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_json", nargs="?", help="Output JSON path")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument(
        "--sample-start", type=int, default=0, help="Sample range start"
    )
    parser.add_argument("--sample-end", type=int, default=None, help="Sample range end")
    parser.add_argument(
        "--direction", default="enc", choices=["enc", "dec"], help="Enc or Dec"
    )
    parser.add_argument("--threshold", type=float, default=4.0, help="HW threshold")
    parser.add_argument(
        "--multiple-thresholds", default=None, help="Comma-separated thresholds"
    )
    parser.add_argument("--byte-pos", default=None, help="Byte positions to attack")
    return parser.parse_args()


def main():
    args = parse_args()

    z = zarr.open(args.input_zarr, mode="r")
    tile = "/0/0/"

    key = z[f"{tile}key"][:]
    if getattr(key, "ndim", 1) == 2:
        key = key[0]

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.input_zarr), "result"
    )
    os.makedirs(output_dir, exist_ok=True)

    config = {
        "sample_start": args.sample_start,
        "sample_end": args.sample_end,
        "direction": args.direction,
        "threshold": args.threshold,
    }

    if args.byte_pos:
        config["byte_pos"] = [int(x) for x in args.byte_pos.split(",")]

    if args.multiple_thresholds:
        config["multiple_thresholds"] = [
            float(x) for x in args.multiple_thresholds.split(",")
        ]

    print(f"DPA Analysis: {args.input_zarr}")
    print(f"Direction: {args.direction}, Threshold: {args.threshold}")

    analyzer = DPAAnalyzer(config=config)
    result = analyzer.analyze(
        args.input_zarr,
        input_path=args.input_zarr,
        output_dir=output_dir,
    )

    output_data = {
        "key_byte": int(result.best_keys[3]) if result.best_keys else None,
        "known_key": "".join(f"{b:02x}" for b in key),
        "recovered_key": "".join(f"{b:02x}" for b in result.best_keys),
        "num_traces": result.num_traces,
        "threshold": result.threshold,
        "direction": result.direction,
        "top_candidates": result.top_candidates,
        "sample_range": result.metadata.get("sample_range"),
    }

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to {args.output_json}")
    else:
        print(f"Recovered key: {output_data['recovered_key']}")
        print(f"Known key:     {output_data['known_key']}")
        for tc in result.top_candidates:
            print(f"  Byte {tc['byte']:02d}: {hex(tc.get('best_key', 0))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
