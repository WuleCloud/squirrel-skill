"""DTW Alignment for test traces."""

from __future__ import annotations

import numpy as np
import zarr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def align(input_path: str, output_path: str, radius: int = 3, plot_path: str | None = None) -> np.ndarray:
    """Align traces using DTW.

    Args:
        input_path: Input zarr path
        output_path: Output zarr path
        radius: DTW radius
        plot_path: Comparison plot path (optional)

    Returns:
        Aligned traces
    """
    from squirrel.preprocessing.Resync_DTW.dtw import DTWAligner

    z = zarr.open(input_path, "r")
    traces = z["/0/0/traces"][:]
    shifts = z["/0/0/shifts"][:] if "/0/0/shifts" in z else None

    if shifts is not None:
        print(f"Loaded {len(traces)} traces, shift range: [{shifts.min()}, {shifts.max()}]")
    else:
        print(f"Loaded {len(traces)} traces (no shifts metadata)")

    aligner = DTWAligner(config={"radius": radius})
    aligned = aligner.align(traces, ref_trace_idx=0)

    z_out = zarr.open(output_path, "w")
    z_out.create_dataset("/0/0/traces", data=aligned)
    print("Saved aligned traces")

    if plot_path:
        fig, axes = plt.subplots(2, 1, figsize=(16, 10))
        [axes[0].plot(traces[i], alpha=0.4, linewidth=0.8) for i in range(min(15, len(traces)))]
        axes[0].set_title("Original Traces")
        axes[0].set_xlabel("Sample")
        axes[0].set_ylabel("Amplitude")
        axes[0].grid(alpha=0.3)

        [axes[1].plot(aligned[i], alpha=0.4, linewidth=0.8) for i in range(min(15, len(aligned)))]
        axes[1].set_title("Aligned Traces (after DTW)")
        axes[1].set_xlabel("Sample")
        axes[1].set_ylabel("Amplitude")
        axes[1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print("Saved comparison plot")

    return aligned


def main():
    """CLI entry point."""
    import sys

    input_path = sys.argv[1] if len(sys.argv) > 1 else "./traces/dtw_original.zarr"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "./result/dtw_aligned.zarr"
    radius = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    plot_path = sys.argv[4] if len(sys.argv) > 4 else "./result/dtw_comparison.png"

    align(input_path, output_path, radius, plot_path)


if __name__ == "__main__":
    main()