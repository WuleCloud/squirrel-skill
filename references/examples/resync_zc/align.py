#!/usr/bin/env python3
"""Align traces using ResyncZC (Zero-Crossing based alignment)."""

import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr
import matplotlib.pyplot as plt

from squirrel.preprocessing.Resync_ZC import ResyncZCAligner


def parse_args():
    parser = argparse.ArgumentParser(description="Align traces using zero-crossing detection")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_zarr", help="Output Zarr path for aligned traces")
    parser.add_argument("ref_trace_idx", type=int, default=0, help="Reference trace index")
    parser.add_argument("comparison_png", nargs="?", help="Optional: comparison plot output path")
    parser.add_argument("--zc-level", type=float, default=0.0, help="Zero-crossing level")
    parser.add_argument("--bin-length", type=int, default=0, help="Target bin length (0 = auto)")
    parser.add_argument("--interactive", action="store_true", help="Show interactive plot (requires display)")
    return parser.parse_args()


def main():
    args = parse_args()

    import matplotlib
    if args.interactive:
        matplotlib.use("TkAgg")
    else:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print(f"Loading traces from: {args.input_zarr}")
    z = zarr.open(args.input_zarr, mode="r")
    traces = z["/0/0/traces"][:]
    labels = z["/0/0/labels"][:] if "/0/0/labels" in z else None

    print(f"Loaded {traces.shape[0]} traces, {traces.shape[1]} samples")

    aligner = ResyncZCAligner(
        config={
            "ref_trace_idx": args.ref_trace_idx,
            "zc_level": args.zc_level,
            "bin_length": args.bin_length,
        }
    )

    print("Aligning traces using zero-crossing resampling...")
    result = aligner.analyze(traces)
    aligned_traces = result.metadata["aligned_traces"]

    print(f"Aligned: {result.num_aligned}/{result.num_traces}")
    print(f"Zero-crossing points: {result.num_zc_points}")

    os.makedirs(os.path.dirname(args.output_zarr), exist_ok=True)

    store = zarr.DirectoryStore(args.output_zarr)
    z_out = zarr.group(store=store, overwrite=True)
    z_out.create_dataset("/0/0/traces", data=aligned_traces, compressor=zarr.codecs.Zstd())
    if labels is not None:
        z_out.create_dataset("/0/0/labels", data=labels, compressor=zarr.codecs.Zstd())

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
        axes[1].set_title(f"Aligned Traces (After ResyncZC) - showing traces 0-{num_show-1}")
        axes[1].set_xlabel("Sample")
        axes[1].set_ylabel("Amplitude")
        axes[1].grid(alpha=0.3)
        axes[1].legend(loc="upper right", fontsize=7, ncol=3)

        plt.tight_layout()
        os.makedirs(os.path.dirname(args.comparison_png), exist_ok=True)
        plt.savefig(args.comparison_png, dpi=150, bbox_inches="tight")
        print(f"Plot saved: {args.comparison_png}")
        if args.interactive:
            print("Showing interactive plot (close window to continue)...")
            plt.show()
        else:
            plt.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())