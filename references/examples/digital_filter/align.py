#!/usr/bin/env python3
"""Apply digital filter to traces."""

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

from squirrel.preprocessing.DigitalFilter import DigitalFilter


def parse_args():
    parser = argparse.ArgumentParser(description="Apply digital filter to traces")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_zarr", help="Output Zarr path for filtered traces")
    parser.add_argument("filter_type", default="low", help="Filter type: low, high, bandpass, bandstop")
    parser.add_argument("freq1", type=float, default=0.1, help="First critical frequency (0-1)")
    parser.add_argument("freq2", type=float, default=0.3, help="Second critical frequency (0-1)")
    parser.add_argument("order", type=int, default=5, help="Filter order")
    parser.add_argument("comparison_png", nargs="?", help="Optional: comparison plot output path")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading traces from: {args.input_zarr}")
    z = zarr.open(args.input_zarr, mode="r")
    traces = z["/0/0/traces"][:]
    labels = z["/0/0/labels"][:] if "/0/0/labels" in z else None

    print(f"Loaded {traces.shape[0]} traces, {traces.shape[1]} samples")
    print(f"Filter: {args.filter_type}, freq1={args.freq1}, freq2={args.freq2}, order={args.order}")

    aligner = DigitalFilter(
        config={
            "filter_type": args.filter_type,
            "freq1": args.freq1,
            "freq2": args.freq2,
            "order": args.order,
        }
    )

    print("Applying filter...")
    result = aligner.analyze(traces)
    filtered_traces = result.metadata["filtered_traces"]

    print(f"Filtered: {result.num_traces} traces")

    os.makedirs(os.path.dirname(args.output_zarr), exist_ok=True)

    store = zarr.DirectoryStore(args.output_zarr)
    z_out = zarr.group(store=store, overwrite=True)
    z_out.create_dataset("/0/0/traces", data=filtered_traces, compressor=zarr.codecs.Zstd())
    if labels is not None:
        z_out.create_dataset("/0/0/labels", data=labels, compressor=zarr.codecs.Zstd())

    print(f"Saved filtered traces: {args.output_zarr}")

    if args.comparison_png:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        num_show = min(50, traces.shape[0])
        colors = plt.cm.viridis(np.linspace(0, 1, num_show))

        # Left: Time domain
        for i in range(num_show):
            axes[0, 0].plot(traces[i], alpha=0.6, linewidth=0.8, color=colors[i], label=f"trace {i}")
        axes[0, 0].set_title(f"Original Traces (Before Filtering) - showing traces 0-{num_show-1}")
        axes[0, 0].set_xlabel("Sample")
        axes[0, 0].set_ylabel("Amplitude")
        axes[0, 0].grid(alpha=0.3)
        axes[0, 0].legend(loc="upper right", fontsize=7, ncol=3)

        for i in range(num_show):
            axes[1, 0].plot(filtered_traces[i], alpha=0.6, linewidth=0.8, color=colors[i], label=f"trace {i}")
        axes[1, 0].set_title(f"Filtered Traces (After {args.filter_type} Filter) - showing traces 0-{num_show-1}")
        axes[1, 0].set_xlabel("Sample")
        axes[1, 0].set_ylabel("Amplitude")
        axes[1, 0].grid(alpha=0.3)
        axes[1, 0].legend(loc="upper right", fontsize=7, ncol=3)

        # Right: Frequency domain
        # Use average trace for frequency visualization
        avg_trace = np.mean(traces[:num_show], axis=0)
        avg_filtered = np.mean(filtered_traces[:num_show], axis=0)

        # Compute FFT
        n_samples = avg_trace.shape[0]
        freqs = np.fft.rfftfreq(n_samples)
        spectrum_orig = np.abs(np.fft.rfft(avg_trace))
        spectrum_filtered = np.abs(np.fft.rfft(avg_filtered))

        axes[0, 1].plot(freqs, spectrum_orig, color="blue", linewidth=0.8)
        axes[0, 1].set_title(f"Original Spectrum (FFT) - Average of {num_show} traces")
        axes[0, 1].set_xlabel("Normalized Frequency")
        axes[0, 1].set_ylabel("Magnitude")
        axes[0, 1].grid(alpha=0.3)
        axes[0, 1].set_xlim([0, 0.5])

        axes[1, 1].plot(freqs, spectrum_filtered, color="orange", linewidth=0.8)
        axes[1, 1].set_title(f"Filtered Spectrum (FFT) - Average of {num_show} traces")
        axes[1, 1].set_xlabel("Normalized Frequency")
        axes[1, 1].set_ylabel("Magnitude")
        axes[1, 1].grid(alpha=0.3)
        axes[1, 1].set_xlim([0, 0.5])

        plt.tight_layout()
        os.makedirs(os.path.dirname(args.comparison_png), exist_ok=True)
        plt.savefig(args.comparison_png, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {args.comparison_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
