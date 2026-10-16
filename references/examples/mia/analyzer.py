#!/usr/bin/env python3
"""MIA analysis script."""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import zarr

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

from squirrel.analysis.mia import MIAAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Run MIA analysis")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_zarr", nargs="?", help="Output Zarr path")
    parser.add_argument("--leakage-model", default="hamming_weight")
    parser.add_argument("--num-subkeys", type=int, default=16)
    parser.add_argument("--range-start", type=int, default=0)
    parser.add_argument("--range-end", type=int, default=None)
    parser.add_argument(
        "--output-dir", help="Output directory for result visualizations"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    z = zarr.open(args.input_zarr, mode="r")
    tile = "/0/0/"

    traces = z[f"{tile}traces"][:]
    plaintext = z[f"{tile}plaintext"][:] if f"{tile}plaintext" in z else None
    key = z[f"{tile}key"][:] if f"{tile}key" in z else None

    print(f"Loaded {traces.shape[0]} traces, {traces.shape[1]} samples")

    if plaintext is None:
        print("ERROR: MIA requires plaintext data")
        return 1

    analyzer = MIAAnalyzer(
        config={
            "leakage_model": args.leakage_model,
            "num_subkeys": args.num_subkeys,
            "range_start": args.range_start,
            "range_end": args.range_end,
        }
    )

    result = analyzer.analyze(
        traces,
        plaintext=plaintext,
        key=key,
    )

    print(f"\nMIA Results:")
    print(f"  Method: {result.method}")
    print(f"  Leakage model: {result.leakage_model}")
    print(f"  Key guess: {[hex(b) for b in result.key_guess]}")

    if key is not None:
        key_list = list(key)
        correct = sum(1 for i, g in enumerate(result.key_guess) if g == key_list[i])
        print(f"  Known key: {[hex(b) for b in key_list]}")
        print(f"  Correct bytes: {correct}/{len(key_list)}")

    if args.output_zarr:
        os.makedirs(os.path.dirname(args.output_zarr), exist_ok=True)
        store = zarr.DirectoryStore(args.output_zarr)
        z_out = zarr.group(store=store, overwrite=True)
        z_out.create_dataset(
            "/0/0/key_guess", data=np.array(result.key_guess, dtype=np.uint8)
        )

    if args.output_dir:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(args.output_dir, exist_ok=True)
        num_bytes = len(result.best_guesses)

        fig1, axes1 = plt.subplots(4, 4, figsize=(20, 16))
        axes1 = axes1.flatten()

        for i, guess in enumerate(result.best_guesses):
            ax = axes1[i]
            if i < num_bytes and result.mutual_informations:
                mi_data = result.mutual_informations[i]
                ax.plot(mi_data, linewidth=0.8, alpha=0.9)
                ax.set_title(
                    f"Byte {i}: 0x{guess['guess']:02X} (correct={guess['correct']})",
                    fontsize=10,
                )
                ax.set_xlabel("Sample")
                ax.set_ylabel("Max MI")
                ax.grid(True, alpha=0.3)

        plt.suptitle(
            f"MIA Mutual Information vs Time - {result.leakage_model}",
            fontsize=14,
            y=1.01,
        )
        plt.tight_layout()
        fig1.savefig(
            os.path.join(args.output_dir, "mia_mi_vs_time.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig1)
        print(f"MI vs Time saved to: {args.output_dir}/mia_mi_vs_time.png")

        fig2, axes2 = plt.subplots(4, 4, figsize=(20, 16))
        axes2 = axes2.flatten()

        for bnum in range(min(16, num_bytes)):
            ax = axes2[bnum]
            if result.mi_matrix and bnum < len(result.mi_matrix):
                mi_mat = result.mi_matrix[bnum]
                best_kg = result.key_guess[bnum]
                correct = (
                    result.best_guesses[bnum]["correct"]
                    if bnum < len(result.best_guesses)
                    else False
                )

                max_mi_per_kg = np.max(mi_mat, axis=0)
                ax.plot(max_mi_per_kg, linewidth=0.5, alpha=0.8)
                ax.axvline(
                    x=best_kg,
                    color="r" if not correct else "g",
                    linestyle="--",
                    linewidth=1.5,
                    label=f"Best: 0x{best_kg:02X}",
                )
                ax.set_title(f"Byte {bnum}", fontsize=10)
                ax.set_xlabel("Key Guess (0-255)")
                ax.set_ylabel("MI")
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)

        plt.suptitle(
            "MIA MI vs Key Guess (0-255) - 16 Bytes",
            fontsize=14,
            y=1.01,
        )
        plt.tight_layout()
        fig2.savefig(
            os.path.join(args.output_dir, "mia_mi_vs_key.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig2)
        print(f"MI vs Key saved to: {args.output_dir}/mia_mi_vs_key.png")

        fig3, ax3 = plt.subplots(figsize=(16, 6))
        num_display = min(10, traces.shape[0])
        for i in range(num_display):
            ax3.plot(traces[i], linewidth=0.5, alpha=0.7, label=f"Trace {i}")
        ax3.set_title(f"Original Traces (first {num_display} traces)", fontsize=12)
        ax3.set_xlabel("Sample")
        ax3.set_ylabel("Amplitude")
        ax3.legend(fontsize=8, loc="upper right")
        ax3.grid(True, alpha=0.3)
        plt.tight_layout()
        fig3.savefig(
            os.path.join(args.output_dir, "mia_original_traces.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig3)
        print(f"Original Traces saved to: {args.output_dir}/mia_original_traces.png")

    return 0


if __name__ == "__main__":
    sys.exit(main())
