#!/usr/bin/env python3
"""Apply normalize to traces."""

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

from squirrel.preprocessing.Normalize import Normalize


def parse_args():
    parser = argparse.ArgumentParser(description="Apply normalize to traces")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_zarr", help="Output Zarr path")
    parser.add_argument("mode", default="mean", help="Normalization mode: mean or mean_stddev")
    parser.add_argument("comparison_png", nargs="?", help="Optional comparison plot path")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading traces from: {args.input_zarr}")
    z = zarr.open(args.input_zarr, mode="r")
    traces = z["/0/0/traces"][:]
    labels = z["/0/0/labels"][:] if "/0/0/labels" in z else None

    print(f"Loaded {traces.shape[0]} traces, {traces.shape[1]} samples")
    print(f"Mode: {args.mode}")

    normalizer = Normalize(config={"mode": args.mode})

    print("Applying normalization...")
    result = normalizer.analyze(traces)
    normalized_traces = result.metadata["normalized_traces"]

    print(f"Normalized: {result.num_traces} traces")

    os.makedirs(os.path.dirname(args.output_zarr), exist_ok=True)

    store = zarr.DirectoryStore(args.output_zarr)
    z_out = zarr.group(store=store, overwrite=True)
    z_out.create_dataset("/0/0/traces", data=normalized_traces, compressor=zarr.codecs.Zstd())
    if labels is not None:
        z_out.create_dataset("/0/0/labels", data=labels, compressor=zarr.codecs.Zstd())

    print(f"Saved normalized traces: {args.output_zarr}")

    if args.comparison_png:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        num_show = min(50, traces.shape[0])
        colors = plt.cm.viridis(np.linspace(0, 1, num_show))

        for i in range(num_show):
            axes[0, 0].plot(traces[i], alpha=0.6, linewidth=0.8, color=colors[i])
        axes[0, 0].set_title(f"Original Traces (Before Normalization) - showing {num_show} traces")
        axes[0, 0].set_xlabel("Sample")
        axes[0, 0].set_ylabel("Amplitude")
        axes[0, 0].grid(alpha=0.3)

        for i in range(num_show):
            axes[1, 0].plot(normalized_traces[i], alpha=0.6, linewidth=0.8, color=colors[i])
        axes[1, 0].set_title(f"Normalized Traces (After {args.mode} Normalization) - showing {num_show} traces")
        axes[1, 0].set_xlabel("Sample")
        axes[1, 0].set_ylabel("Amplitude")
        axes[1, 0].grid(alpha=0.3)

        avg_orig = np.mean(traces[:num_show], axis=0)
        avg_norm = np.mean(normalized_traces[:num_show], axis=0)

        axes[0, 1].hist(traces[:num_show].flatten(), bins=50, alpha=0.7, color="blue")
        axes[0, 1].set_title(f"Original Trace Distribution - Mean: {np.mean(traces):.4f}, Std: {np.std(traces):.4f}")
        axes[0, 1].set_xlabel("Amplitude")
        axes[0, 1].set_ylabel("Count")
        axes[0, 1].grid(alpha=0.3)

        axes[1, 1].hist(normalized_traces[:num_show].flatten(), bins=50, alpha=0.7, color="orange")
        axes[1, 1].set_title(f"Normalized Trace Distribution - Mean: {np.mean(normalized_traces):.4f}, Std: {np.std(normalized_traces):.4f}")
        axes[1, 1].set_xlabel("Amplitude")
        axes[1, 1].set_ylabel("Count")
        axes[1, 1].grid(alpha=0.3)

        plt.tight_layout()
        os.makedirs(os.path.dirname(args.comparison_png), exist_ok=True)
        plt.savefig(args.comparison_png, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {args.comparison_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
