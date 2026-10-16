#!/usr/bin/env python3
"""Run Channel Estimate analysis on traces."""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr

from squirrel.analysis.channel_estimate import ChannelEstimateAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Run Channel Estimate analysis")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_json", nargs="?", help="Output JSON path for results")
    parser.add_argument(
        "--leakage-model", default="sbox_output", choices=["sbox_output", "pt_key_xor"]
    )
    parser.add_argument("--fit-ratio", type=float, default=0.8)
    parser.add_argument("--use-svd", type=lambda x: x.lower() == "true", default=True)
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

    analyzer = ChannelEstimateAnalyzer(
        config={
            "leakage_model": args.leakage_model,
            "fit_ratio": args.fit_ratio,
            "use_svd": args.use_svd,
            "num_subkeys": 16,
        }
    )

    result = analyzer.analyze(
        traces, plaintext=plaintext, key=key, input_path=args.input_zarr
    )

    print(f"Channel Estimate Results:")
    print(f"  Key guess: {[hex(b) for b in result.key_guess]}")
    print(f"  Best guesses (first 4 bytes):")
    for i, guesses in enumerate(result.best_guesses[:4]):
        print(
            f"    Byte {i}: 0x{guesses[0]['guess']:02X} (SSE={guesses[0]['sse']:.2f}, PGE={result.pge[i]})"
        )

    if key is not None:
        print(f"  Expected key: {[hex(b) for b in key]}")
        pge_valid = sum(1 for p in result.pge if p < 10)
        print(f"  PGE < 10 for {pge_valid}/{len(result.pge)} bytes")

    if args.output_json:
        import json

        output_data = {
            "key_guess": [hex(b) for b in result.key_guess],
            "best_guesses": [
                [{"guess": g["guess"], "sse": float(g["sse"])} for g in guesses]
                for guesses in result.best_guesses
            ],
            "pge": result.pge,
            "num_traces_fit": result.num_traces_fit,
            "num_traces_test": result.num_traces_test,
            "leakage_model": result.metadata.get("leakage_model"),
        }
        with open(args.output_json, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {args.output_json}")

    if args.output_dir:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(args.output_dir, exist_ok=True)

        num_bytes = len(result.best_guesses)

        fig1, axes1 = plt.subplots(4, 4, figsize=(20, 16))
        axes1 = axes1.flatten()

        for i, sses in enumerate(result.all_sses):
            ax = axes1[i]
            ax.plot(sses, linewidth=0.8, alpha=0.9)
            ax.set_title(
                f"Byte {i}: 0x{result.best_guesses[i][0]['guess']:02X} (PGE={result.pge[i]})",
                fontsize=10,
            )
            ax.set_xlabel("Key Guess (0-255)")
            ax.set_ylabel("SSE")
            ax.grid(True, alpha=0.3)
            ax.axhline(
                y=sses[result.best_guesses[i][0]["guess"]],
                color="red",
                linestyle="--",
                alpha=0.5,
            )

        plt.suptitle(
            f"Channel Estimate SSE vs Key Guess - {result.metadata.get('leakage_model', 'Unknown')}",
            fontsize=14,
            y=1.01,
        )
        plt.tight_layout()
        fig1.savefig(
            os.path.join(args.output_dir, "ce_sse_vs_guess.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig1)
        print(f"SSE vs Guess saved to: {args.output_dir}/ce_sse_vs_guess.png")

        fig2, axes2 = plt.subplots(1, 2, figsize=(16, 6))

        ax2_0 = axes2[0]
        pge_values = result.pge
        ax2_0.bar(range(16), pge_values, color="steelblue", alpha=0.8)
        ax2_0.axhline(y=10, color="red", linestyle="--", label="PGE threshold=10")
        ax2_0.set_xlabel("Byte")
        ax2_0.set_ylabel("PGE (Guessing Entropy)")
        ax2_0.set_title("PGE per Byte")
        ax2_0.legend()
        ax2_0.grid(True, alpha=0.3, axis="y")

        ax2_1 = axes2[1]
        best_sses = [result.all_sses[i][result.key_guess[i]] for i in range(16)]
        ax2_1.bar(range(16), best_sses, color="seagreen", alpha=0.8)
        ax2_1.set_xlabel("Byte")
        ax2_1.set_ylabel("Best SSE")
        ax2_1.set_title("Best SSE per Byte (Correct Key)")
        ax2_1.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        fig2.savefig(
            os.path.join(args.output_dir, "ce_pge_and_sse.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig2)
        print(f"PGE and SSE saved to: {args.output_dir}/ce_pge_and_sse.png")

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
            os.path.join(args.output_dir, "ce_original_traces.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig3)
        print(f"Original Traces saved to: {args.output_dir}/ce_original_traces.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
