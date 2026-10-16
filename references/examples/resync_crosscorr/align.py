from __future__ import annotations

import numpy as np
import zarr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def align(input_path: str, output_path: str, ref_trace_idx: int = 0, plot_path: str | None = None, window: tuple[int, int] | None = None) -> np.ndarray:
    from squirrel.preprocessing.Resync_CrossCorr import ResyncCrossCorrAligner

    z = zarr.open(input_path, "r")
    traces = z["/0/0/traces"][:]
    shifts = z["/0/0/shifts"][:] if "/0/0/shifts" in z else None

    print(f"Loaded {len(traces)} traces")
    if shifts is not None:
        print(f"Shift range: [{shifts.min()}, {shifts.max()}]")

    num_samples = traces.shape[1]
    if window is None or window == (0, 0):
        window = (450, 550)

    aligner = ResyncCrossCorrAligner(config={"ref_trace_idx": ref_trace_idx, "window": window})
    result = aligner.analyze(traces)
    aligned = result.metadata["aligned_traces"]

    z_out = zarr.open(output_path, "w")
    z_out.create_dataset("/0/0/traces", data=aligned)
    if shifts is not None:
        z_out.create_dataset("/0/0/shifts", data=shifts)
    print("Saved aligned traces")

    if plot_path:
        fig, axes = plt.subplots(2, 1, figsize=(16, 10))
        [axes[0].plot(traces[i], alpha=0.4, linewidth=0.8) for i in range(min(15, len(traces)))]
        axes[0].set_title("Original Traces")
        axes[0].set_xlabel("Sample")
        axes[0].set_ylabel("Amplitude")
        axes[0].grid(alpha=0.3)

        [axes[1].plot(aligned[i], alpha=0.4, linewidth=0.8) for i in range(min(15, len(aligned)))]
        axes[1].set_title("Aligned Traces (after CrossCorr)")
        axes[1].set_xlabel("Sample")
        axes[1].set_ylabel("Amplitude")
        axes[1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print("Saved comparison plot")

    return aligned


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Align traces using cross-correlation")
    parser.add_argument("input_zarr", help="Input zarr path")
    parser.add_argument("output_zarr", help="Output zarr path")
    parser.add_argument("ref_trace_idx", nargs="?", type=int, default=0, help="Reference trace index")
    parser.add_argument("comparison_png", nargs="?", help="Optional comparison plot path")
    parser.add_argument("--window-start", type=int, default=0, help="Window start")
    parser.add_argument("--window-end", type=int, default=0, help="Window end (0 = use full trace)")
    args = parser.parse_args()

    window = None
    if args.window_end > 0:
        window = (args.window_start, args.window_end)

    align(args.input_zarr, args.output_zarr, args.ref_trace_idx, args.comparison_png, window)


if __name__ == "__main__":
    main()