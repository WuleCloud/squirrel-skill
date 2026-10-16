#!/usr/bin/env python3
"""Template Attack analyzer script."""

import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import json
import zarr

from squirrel.analysis.template import TemplateAnalyzer


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Template Attack Analyzer")
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
    parser.add_argument(
        "--num-pois", type=int, default=5, help="Number of POIs per byte"
    )
    parser.add_argument("--poi-spacing", type=int, default=5, help="POI spacing")
    parser.add_argument("--byte-pos", default=None, help="Byte positions to attack")
    return parser.parse_args()


def main():
    args = parse_args()

    z = zarr.open(args.input_zarr, mode="r")
    profile_tile = "/0/0/"
    attack_tile = "/1/0/"

    profile_key = z[f"{profile_tile}key"][:]
    if getattr(profile_key, "ndim", 1) == 2:
        profile_key = profile_key[0]

    attack_key = z[f"{attack_tile}key"][:]
    if getattr(attack_key, "ndim", 1) == 2:
        attack_key = attack_key[0]

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.input_zarr), "result"
    )
    os.makedirs(output_dir, exist_ok=True)

    config = {
        "sample_start": args.sample_start,
        "sample_end": args.sample_end,
        "direction": args.direction,
        "num_pois": args.num_pois,
        "poi_spacing": args.poi_spacing,
    }

    if args.byte_pos:
        config["byte_pos"] = [int(x) for x in args.byte_pos.split(",")]

    print(f"Template Attack Analysis: {args.input_zarr}")
    print(
        f"Direction: {args.direction}, POIs: {args.num_pois}, Spacing: {args.poi_spacing}"
    )

    analyzer = TemplateAnalyzer(config=config)
    result = analyzer.analyze(
        args.input_zarr,
        input_path=args.input_zarr,
        output_dir=output_dir,
    )

    output_data = {
        "known_key": "".join(f"{b:02x}" for b in attack_key),
        "recovered_key": "".join(f"{b:02x}" for b in result.best_keys),
        "num_profile_traces": result.num_profile_traces,
        "num_attack_traces": result.num_attack_traces,
        "num_pois": result.num_pois,
        "poi_spacing": result.poi_spacing,
        "direction": result.direction,
        "top_candidates": result.top_candidates,
        "pois": result.metadata.get("pois", {}),
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
