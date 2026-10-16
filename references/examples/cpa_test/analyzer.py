#!/usr/bin/env python3
"""Run CPA analysis on traces."""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT + "/src")

import numpy as np
import zarr

from squirrel.analysis.cpa import CPAAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Run CPA analysis")
    parser.add_argument("input_zarr", help="Input Zarr path")
    parser.add_argument("output_json", nargs="?", help="Output JSON path for results")
    parser.add_argument(
        "--leakage-model",
        default="sbox_output",
        choices=[
            "sbox_output",
            "pt_key_xor",
            "inv_sbox_output",
            "lastround_hw",
            "lastround_state_diff",
            "lastround_state_diff_alt",
            "pipeline_diff",
            "half_pipeline_diff",
            "sbox_in_out_diff",
            "sbox_input_successive",
            "sbox_output_successive",
        ],
    )
    parser.add_argument("--num-subkeys", type=int, default=16)
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
    ciphertext = z[f"{tile}ciphertext"][:] if f"{tile}ciphertext" in z else None

    print(f"Loaded {traces.shape[0]} traces with {traces.shape[1]} samples")

    analyzer = CPAAnalyzer(
        config={
            "leakage_model": args.leakage_model,
            "num_subkeys": args.num_subkeys,
        }
    )

    result = analyzer.analyze(
        traces,
        plaintext=plaintext,
        ciphertext=ciphertext,
        key=key,
        input_path=args.input_zarr,
    )

    print(f"CPA Results:")
    print(f"  Key guess: {[hex(b) for b in result.key_guess]}")
    print(f"  Best guesses (first 4 bytes):")
    for i, guess in enumerate(result.best_guesses[:4]):
        print(
            f"    Byte {i}: 0x{guess['guess']:02X} (corr={guess['correlation']:.4f}, pge={guess['pge']})"
        )

    if key is not None:
        print(f"  Expected key: {[hex(b) for b in key]}")
        pge_valid = sum(1 for p in result.pge if p < 10)
        print(f"  PGE < 10 for {pge_valid}/{len(result.pge)} bytes")

    if args.output_json:
        import json

        output_data = {
            "key_guess": [hex(b) for b in result.key_guess],
            "best_guesses": result.best_guesses,
            "pge": result.pge,
            "num_traces": result.num_traces,
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

        for i, guess in enumerate(result.best_guesses):
            ax = axes1[i]
            if i < num_bytes and result.correlations:
                corr_data = np.abs(result.correlations[i])
                max_corr_per_sample = np.max(corr_data, axis=0)
                ax.plot(max_corr_per_sample, linewidth=0.8, alpha=0.9)
                ax.set_title(
                    f"Byte {i}: 0x{guess['guess']:02X} (PGE={guess['pge']})",
                    fontsize=10,
                )
                ax.set_xlabel("Sample")
                ax.set_ylabel("Max Correlation")
                ax.grid(True, alpha=0.3)

        plt.suptitle(
            f"CPA Correlation vs Time - {result.metadata.get('leakage_model', 'Unknown')}",
            fontsize=14,
            y=1.01,
        )
        plt.tight_layout()
        fig1.savefig(
            os.path.join(args.output_dir, "cpa_correlation_vs_time.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig1)
        print(
            f"Correlation vs Time saved to: {args.output_dir}/cpa_correlation_vs_time.png"
        )

        fig2, axes2 = plt.subplots(4, 4, figsize=(20, 16))
        axes2 = axes2.flatten()

        for bnum in range(16):
            ax = axes2[bnum]
            if result.correlations:
                corr_data = np.abs(result.correlations[bnum])
                for t in range(corr_data.shape[1]):
                    ax.plot(corr_data[:, t], linewidth=0.5, alpha=0.6)
                ax.set_title(f"Byte {bnum}", fontsize=10)
                ax.set_xlabel("Key Guess (0-255)")
                ax.set_ylabel("Correlation")
                ax.grid(True, alpha=0.3)

        plt.suptitle(
            "CPA Correlation vs Key Guess (0-255) - 16 Bytes",
            fontsize=14,
            y=1.01,
        )
        plt.tight_layout()
        fig2.savefig(
            os.path.join(args.output_dir, "cpa_max_correlation_vs_time.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig2)
        print(
            f"Max Correlation vs Time saved to: {args.output_dir}/cpa_max_correlation_vs_time.png"
        )

        # Figure 3: Original trace visualization (first 10 traces)
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
            os.path.join(args.output_dir, "cpa_original_traces.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig3)
        print(f"Original Traces saved to: {args.output_dir}/cpa_original_traces.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
