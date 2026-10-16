#!/usr/bin/env python3
"""Align traces using SAD algorithm."""

import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from squirrel.preprocessing.Resync_SAD import SADAligner


def parse_args():
    parser = argparse.ArgumentParser(description="Align traces using SAD")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_zarr", help="Output Zarr path for aligned traces")
    parser.add_argument("ref_trace_idx", type=int, default=0, help="Reference trace index")
    parser.add_argument("comparison_png", nargs="?", help="Optional comparison plot output path")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading traces from: {args.input_zarr}")
    z = zarr.open(args.input_zarr, mode="r")
    traces = z["/0/0/traces"][:]
    labels = z["/0/0/labels"][:] if "/0/0/labels" in z else None

    num_samples = traces.shape[1]
    target_window = (num_samples // 4, num_samples // 4 * 3)

    print(f"Loaded {traces.shape[0]} traces, {traces.shape[1]} samples")
    print(f"Using target window: {target_window}")

    aligner = SADAligner(
        config={
            "ref_trace_idx": args.ref_trace_idx,
            "target_window": target_window,
            "max_shift": 50,
        }
    )

    print("Aligning traces...")
    result = aligner.analyze(traces)
    aligned_traces = result.metadata["aligned_traces"]

    print(f"Aligned: {result.num_aligned}/{result.num_traces}")
    print(f"Mean SAD: {result.mean_sad:.2f}")

    os.makedirs(os.path.dirname(args.output_zarr), exist_ok=True)

    store = zarr.DirectoryStore(args.output_zarr)
    z_out = zarr.group(store=store, overwrite=True)
    z_out.create_dataset("/0/0/traces", data=aligned_traces, compressor=zarr.codecs.Zstd())
    if labels is not None:
        z_out.create_dataset("/0/0/labels", data=labels)

    print(f"Saved aligned traces: {args.output_zarr}")

    if args.comparison_png:
        fig, axes = plt.subplots(2, 1, figsize=(16, 10))

        num_show = min(5, traces.shape[0])
        colors = plt.cm.viridis(np.linspace(0, 1, num_show))

        for i in range(num_show):
            axes[0].plot(traces[i], alpha=0.6, linewidth=0.8, color=colors[i], label=f"trace {i}")
        axes[0].set_title(f"Original Traces (Before Alignment) - showing traces 0-{num_show-1}")
        axes[0].set_xlabel("Sample")
        axes[0].set_ylabel("Amplitude")
        axes[0].grid(alpha=0.3)
        axes[0].legend(loc="upper right", fontsize=7, ncol=3)

        for i in range(num_show):
            axes[1].plot(aligned_traces[i], alpha=0.6, linewidth=0.8, color=colors[i], label=f"trace {i}")
        axes[1].set_title(f"Aligned Traces (After SAD) - showing traces 0-{num_show-1}")
        axes[1].set_xlabel("Sample")
        axes[1].set_ylabel("Amplitude")
        axes[1].grid(alpha=0.3)
        axes[1].legend(loc="upper right", fontsize=7, ncol=3)

        plt.tight_layout()
        os.makedirs(os.path.dirname(args.comparison_png), exist_ok=True)
        plt.savefig(args.comparison_png, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {args.comparison_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
