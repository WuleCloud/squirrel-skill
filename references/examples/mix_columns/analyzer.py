#!/usr/bin/env python3
"""Run MixColumns CPA analysis on traces."""

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

from squirrel.analysis.mix_columns import MixColumnsCPAAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Run MixColumns CPA analysis")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_json", nargs="?", help="Output JSON path for results")
    parser.add_argument("--vec-type", default="column", choices=["column", "row"])
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
    key = z[f"{tile}key"][:] if f"{tile}key" in z else None

    print(f"Loaded {traces.shape[0]} traces with {traces.shape[1]} samples")

    analyzer = MixColumnsCPAAnalyzer(
        config={
            "vec_type": args.vec_type,
            "hamming_distance": True,
        }
    )

    result = analyzer.analyze(
        traces, plaintext=plaintext, key=key, input_path=args.input_zarr
    )

    print(f"MixColumns CPA Results:")
    print(f"  Key guess: {[hex(b) for b in result.key_guess]}")
    print(f"  Best guesses (first 4 bytes):")
    for i, guess in enumerate(result.best_guesses[:4]):
        print(
            f"    Byte {i}: 0x{guess['guess']:02X} (corr={guess['correlation']:.4f}, pge={guess['pge']})"
        )

    if key is not None:
        print(f"  Expected key: {[hex(b) for b in key]}")
        pge_zero = sum(1 for p in result.pge if p == 0)
        print(f"  PGE = 0 for {pge_zero}/{len(result.pge)} bytes")

    if args.output_json:
        output_data = {
            "key_guess": [hex(b) for b in result.key_guess],
            "best_guesses": result.best_guesses,
            "pge": result.pge,
            "num_traces": result.num_traces,
            "vec_type": result.metadata.get("vec_type"),
            "hamming_distance": result.metadata.get("hamming_distance"),
        }
        with open(args.output_json, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {args.output_json}")

    if args.output_dir:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(args.output_dir, exist_ok=True)

        if result.correlations:
            fig, axes = plt.subplots(4, 4, figsize=(20, 16))
            axes = axes.flatten()

            for i, guess in enumerate(result.best_guesses):
                ax = axes[i]
                corr_data = np.abs(result.correlations[i])
                max_corr_per_sample = np.max(corr_data, axis=0)
                data_max = max_corr_per_sample.max()
                ax.plot(max_corr_per_sample, linewidth=0.8, alpha=0.9)
                ax.set_ylim(0, data_max * 1.2 if data_max > 0 else 0.01)
                ax.set_title(
                    f"Byte {i}: 0x{guess['guess']:02X} (PGE={guess['pge']})",
                    fontsize=10,
                )
                ax.set_xlabel("Sample")
                ax.set_ylabel("Max Correlation")
                ax.grid(True, alpha=0.3)

            plt.suptitle(
                f"MixColumns CPA Correlation vs Time",
                fontsize=14,
                y=1.01,
            )
            plt.tight_layout()
            fig.savefig(
                os.path.join(args.output_dir, "mix_columns_corr_vs_time.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig)
            print(
                f"Correlation vs Time saved to: {args.output_dir}/mix_columns_corr_vs_time.png"
            )

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
                os.path.join(args.output_dir, "mix_columns_original_traces.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig2)
            print(
                f"Original Traces saved to: {args.output_dir}/mix_columns_original_traces.png"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
