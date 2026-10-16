#!/usr/bin/env python3
"""Run Correlation Analysis on zarr dataset."""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from squirrel.analysis.correlation import CorrelationAnalyzer


TILE = "/0/0/"
DEFAULT_THRESHOLD = 0.3


def run_analysis(
    zarr_path: str,
    output_dir: str,
    threshold: float = DEFAULT_THRESHOLD,
    data_type: str = "plaintext",
) -> dict:
    """Run correlation analysis on zarr dataset."""
    z = zarr.open(zarr_path, "r")

    traces = z[f"{TILE}traces"][:]
    plaintext = z[f"{TILE}plaintext"][:]

    if f"{TILE}leakage_region" in z:
        leakage_region = z[f"{TILE}leakage_region"][:]
    else:
        leakage_region = np.array([400, 600, 4.0])

    print(f"Loaded {traces.shape[0]} traces, {traces.shape[1]} samples")
    print(f"Data type: {data_type}")
    print(f"Leakage region: [{leakage_region[0]}, {leakage_region[1]}]")

    analyzer = CorrelationAnalyzer(
        config={
            "data_type": data_type,
            "correlation_threshold": threshold,
            "sample_range": (0, None),
        }
    )

    result = analyzer.analyze(
        traces=traces,
        plaintext=plaintext,
        input_path=zarr_path,
    )

    print(f"\nCorrelation Analysis Results:")
    print(
        f"  Max correlation: {result.max_correlation_value:.4f} (byte {result.max_correlation_byte}, sample {result.max_correlation_sample})"
    )
    print(f"  Mean |correlation|: {result.correlation_mean_abs:.4f}")
    print(
        f"  Correlation range: [{result.correlation_min:.4f}, {result.correlation_max:.4f}]"
    )

    if result.correlation_matrix is not None:
        corr_matrix = result.correlation_matrix

        num_bytes = corr_matrix.shape[0]
        num_samples = corr_matrix.shape[1]

        plt.figure(figsize=(14, 8))
        plt.imshow(corr_matrix, aspect="auto", cmap="RdBu_r", vmin=-1, vmax=1)
        plt.colorbar(label="Correlation")
        plt.xlabel("Sample Point")
        plt.ylabel("Byte Index")
        plt.title(f"Correlation Analysis - {data_type} HW vs Traces")

        if leakage_region is not None:
            plt.axvline(
                x=leakage_region[0],
                color="green",
                linestyle="--",
                linewidth=2,
                label=f"Leakage region start",
            )
            plt.axvline(
                x=leakage_region[1],
                color="green",
                linestyle="--",
                linewidth=2,
                label=f"Leakage region end",
            )

        plt.legend()
        plt.tight_layout()

        plot_path = os.path.join(output_dir, "correlation_plot.png")
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {plot_path}")

        max_corr_by_sample = np.max(np.abs(corr_matrix), axis=0)
        plt.figure(figsize=(14, 6))
        plt.plot(range(num_samples), max_corr_by_sample, "b-", linewidth=0.8, alpha=0.9)
        plt.axhline(
            y=threshold,
            color="red",
            linestyle="--",
            linewidth=1.2,
            label=f"Threshold = {threshold}",
        )
        plt.axhline(y=-threshold, color="red", linestyle="--", linewidth=1.2)

        if leakage_region is not None:
            plt.axvspan(
                leakage_region[0],
                leakage_region[1],
                alpha=0.2,
                color="orange",
                label="Leakage Region",
            )

        plt.xlim(0, num_samples)
        plt.xlabel("Sample Point")
        plt.ylabel("Max |Correlation|")
        plt.title(f"Correlation vs Sample Point (Max over all bytes)")
        plt.legend(loc="upper right")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        corr_vs_sample_path = os.path.join(output_dir, "correlation_vs_sample.png")
        plt.savefig(corr_vs_sample_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Correlation vs sample plot saved: {corr_vs_sample_path}")

        byte_max_corr = np.max(np.abs(corr_matrix), axis=1)
        plt.figure(figsize=(12, 6))
        plt.bar(range(num_bytes), byte_max_corr)
        plt.xlabel("Byte Index")
        plt.ylabel("Max |Correlation|")
        plt.title(f"Max Correlation by Byte - {data_type}")
        plt.axhline(
            y=threshold, color="red", linestyle="--", label=f"Threshold = {threshold}"
        )
        plt.legend()
        plt.tight_layout()

        byte_plot_path = os.path.join(output_dir, "correlation_by_byte.png")
        plt.savefig(byte_plot_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Byte plot saved: {byte_plot_path}")

        region_start, region_end = int(leakage_region[0]), int(leakage_region[1])
        region_corr = corr_matrix[:, region_start:region_end]
        region_max = np.max(np.abs(region_corr))
        print(
            f"\nLeakage region [{region_start}, {region_end}]: max|correlation| = {region_max:.4f}"
        )

    report = {
        "algorithm": "correlation",
        "input_path": zarr_path,
        "data_type": data_type,
        "threshold": threshold,
        "total_samples": result.total_samples,
        "trace_count": result.trace_count,
        "correlation_min": result.correlation_min,
        "correlation_max": result.correlation_max,
        "correlation_mean_abs": result.correlation_mean_abs,
        "max_correlation_byte": result.max_correlation_byte,
        "max_correlation_sample": result.max_correlation_sample,
        "max_correlation_value": result.max_correlation_value,
        "leakage_region": [
            int(leakage_region[0]),
            int(leakage_region[1]),
            float(leakage_region[2]),
        ],
    }

    report_path = os.path.join(output_dir, "correlation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: {report_path}")

    return report


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python analyzer.py <zarr_path> <output_dir> [threshold] [data_type]"
        )
        sys.exit(1)

    zarr_path = sys.argv[1]
    output_dir = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_THRESHOLD
    data_type = sys.argv[4] if len(sys.argv) > 4 else "plaintext"

    os.makedirs(output_dir, exist_ok=True)

    run_analysis(zarr_path, output_dir, threshold, data_type)


if __name__ == "__main__":
    main()
