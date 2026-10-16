#!/usr/bin/env python3
"""Run SNR analysis on traces."""

import argparse
import os
import sys
import json

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr

from squirrel.analysis.snr import SNRAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Run SNR analysis")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_json", nargs="?", help="Output JSON path for results")
    parser.add_argument(
        "--output-dir", help="Output directory for result visualizations"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    z = zarr.open(args.input_zarr, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:]

    print(f"Loaded {traces.shape[0]} traces with {traces.shape[1]} samples")

    analyzer = SNRAnalyzer()

    result = analyzer.analyze(traces, plaintext=plaintext, input_path=args.input_zarr)

    print(f"SNR Analysis Results:")
    print(f"  Peak SNR: {result.peak_snr_db:.2f} dB at sample {result.peak_sample}")
    print(f"  Num leakage groups: {result.num_leakage_groups}")
    print(f"  Best group size: {result.best_group_size}")

    if args.output_json:
        output_data = {
            "peak_snr_db": result.peak_snr_db,
            "peak_sample": result.peak_sample,
            "num_leakage_groups": result.num_leakage_groups,
            "best_group_size": result.best_group_size,
            "group_sizes": result.metadata.get("group_sizes"),
        }
        with open(args.output_json, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {args.output_json}")

    if args.output_dir:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(args.output_dir, exist_ok=True)

        snr_db = result.snr_db
        if snr_db is not None:
            fig, ax = plt.subplots(figsize=(16, 6))
            ax.plot(snr_db, linewidth=0.8, alpha=0.9)
            ax.axhline(
                y=0,
                color="gray",
                linestyle="-",
                alpha=0.3,
            )
            data_max = snr_db.max()
            ax.set_ylim(min(snr_db.min() - 1, -5), data_max * 1.2)
            ax.set_title(
                f"SNR vs Time (peak={result.peak_snr_db:.2f}dB at sample {result.peak_sample})",
                fontsize=12,
            )
            ax.set_xlabel("Sample")
            ax.set_ylabel("SNR (dB)")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            fig.savefig(
                os.path.join(args.output_dir, "snr_vs_time.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig)
            print(f"SNR vs Time saved to: {args.output_dir}/snr_vs_time.png")

            fig2, ax2 = plt.subplots(figsize=(16, 6))
            num_display = min(10, traces.shape[0])
            for i in range(num_display):
                ax2.plot(traces[i], linewidth=0.5, alpha=0.7, label=f"Trace {i}")
            ax2.set_title(f"Original Traces (first {num_display} traces)", fontsize=12)
            ax2.set_xlabel("Sample")
            ax2.set_ylabel("Amplitude")
            ax2.legend(fontsize=8, loc="upper right")
            ax2.grid(True, alpha=0.3)
            plt.tight_layout()
            fig2.savefig(
                os.path.join(args.output_dir, "snr_original_traces.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig2)
            print(
                f"Original Traces saved to: {args.output_dir}/snr_original_traces.png"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
