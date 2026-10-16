"""TVLA Analysis and Verification."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import zarr


TILE = "/0/0/"


def compute_ttest(fixed: np.ndarray, random: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute t-test between fixed and random traces."""
    mean_fixed = np.mean(fixed, axis=0)
    mean_random = np.mean(random, axis=0)
    var_fixed = np.var(fixed, axis=0, ddof=1)
    var_random = np.var(random, axis=0, ddof=1)

    n_fixed = fixed.shape[0]
    n_random = random.shape[0]
    denominator = np.sqrt(var_fixed / n_fixed + var_random / n_random)
    t_values = (mean_fixed - mean_random) / np.where(denominator > 0, denominator, 1)

    return t_values, denominator


def run_analysis(zarr_path: str, output_dir: str, threshold: float = 4.5) -> dict:
    """Run TVLA analysis on zarr dataset."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    z = zarr.open(zarr_path, "r")

    fixed = z[f"{TILE}fixed_traces"][:]
    random = z[f"{TILE}random_traces"][:]

    t_values, _ = compute_ttest(fixed, random)

    leakage_mask = np.abs(t_values) > threshold
    leakage_points = np.where(leakage_mask)[0].tolist()

    if f"{TILE}leakage_regions" in z:
        leakage_regions = z[f"{TILE}leakage_regions"][:]
    else:
        leakage_window = z[f"{TILE}leakage_window"][:]
        leakage_regions = np.array([[leakage_window[0], leakage_window[1], 0]])

    num_samples = fixed.shape[1]
    n_fixed = fixed.shape[0]
    n_random = random.shape[0]

    x = np.arange(num_samples)

    plt.figure(figsize=(14, 6))
    plt.plot(x, t_values, "b-", linewidth=0.8, alpha=0.9, label="t-value")
    plt.axhline(y=threshold, color="red", linestyle="--", linewidth=1.2, label=f"Threshold = ±{threshold}")
    plt.axhline(y=-threshold, color="red", linestyle="--", linewidth=1.2)
    plt.axhline(y=0, color="gray", linestyle="-", linewidth=0.5, alpha=0.5)

    for i, (start, end, amp) in enumerate(leakage_regions):
        plt.axvspan(start, end, alpha=0.2, color="orange", linewidth=0)
        region_label = chr(ord("A") + i)
        mid = (start + end) // 2
        region_max = max(t_values[int(start) : int(end)])
        y_pos = region_max + 3 if region_max > threshold else 50
        plt.text(mid, y_pos, f"{region_label}", ha="center", va="bottom", fontsize=10, fontweight="bold", color="darkorange")

    plt.xlim(0, num_samples)
    plt.ylim(min(t_values) - 5, max(t_values) + 15)
    plt.xlabel("Sample Point", fontsize=12)
    plt.ylabel("t-value", fontsize=12)
    plt.title("TVLA t-test Analysis Results", fontsize=14, fontweight="bold")
    plt.legend(loc="upper right", fontsize=10)
    plt.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
    plt.tight_layout()

    plot_path = os.path.join(output_dir, "tvla_plot.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Plot saved: {plot_path}")

    report = {
        "algorithm": "AES",
        "input_path": zarr_path,
        "threshold": threshold,
        "total_samples": num_samples,
        "trace_count_fixed": n_fixed,
        "trace_count_random": n_random,
        "encryption_range_start": 0,
        "encryption_range_end": num_samples,
        "ttest_min": float(np.min(t_values)),
        "ttest_max": float(np.max(t_values)),
        "ttest_mean_abs": float(np.mean(np.abs(t_values))),
        "total_leakage_points": len(leakage_points),
        "leakage_points": leakage_points,
        "leakage_regions": [],
    }

    for start, end, amp in leakage_regions:
        report["leakage_regions"].append({
            "start": int(start),
            "end": int(end),
            "amplitude": float(amp),
        })

        region_tvals = t_values[int(start) : int(end)]
        max_abs_t = float(np.max(np.abs(region_tvals)))

        print(f"Region [{int(start)}, {int(end)}]: max|t| = {max_abs_t:.2f}")

    if leakage_points:
        report["first_leakage_point"] = int(leakage_points[0])
        report["first_leakage_tvalue"] = float(t_values[leakage_points[0]])
        report["first_encryption_leakage_point"] = int(leakage_points[0])
        report["first_encryption_leakage_tvalue"] = float(t_values[leakage_points[0]])
    else:
        report["first_leakage_point"] = None
        report["first_leakage_tvalue"] = None
        report["first_encryption_leakage_point"] = None
        report["first_encryption_leakage_tvalue"] = None

    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()

    report_path = os.path.join(output_dir, "tvla_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Report saved: {report_path}")
    print(f"Leakage points: {len(leakage_points)}")

    return report


def verify(zarr_path: str, threshold: float = 4.5) -> bool:
    """Verify TVLA analysis results against known leakage regions."""
    z = zarr.open(zarr_path, "r")

    if f"{TILE}leakage_regions" in z:
        leakage_regions = z[f"{TILE}leakage_regions"][:]
    else:
        leakage_window = z[f"{TILE}leakage_window"][:]
        leakage_regions = np.array([[leakage_window[0], leakage_window[1], 0]])

    fixed = z[f"{TILE}fixed_traces"][:]
    random = z[f"{TILE}random_traces"][:]

    t_values, _ = compute_ttest(fixed, random)

    all_pass = True

    print("")
    print("=== TVLA Verification ===")
    print(f"Threshold: >{threshold}")
    print("")

    for i, (start, end, amp) in enumerate(leakage_regions):
        start, end = int(start), int(end)
        region_tvals = t_values[start:end]
        max_abs_t = np.max(np.abs(region_tvals))
        status = "PASS" if max_abs_t > threshold else "FAIL"
        if max_abs_t <= threshold:
            all_pass = False
        region_letter = chr(ord("A") + i)
        print(f"Region {region_letter}: [{start}, {end}] max|t| = {max_abs_t:.2f} [{status}]")

    print("")
    if all_pass:
        print("=== ALL REGIONS PASS ===")
    else:
        print("=== VERIFICATION FAILED ===")

    return all_pass


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python verifier.py <command> [args]")
        print("Commands:")
        print("  analyze <zarr_path> <output_dir> [threshold]")
        print("  verify <zarr_path> [threshold]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "analyze":
        zarr_path = sys.argv[2] if len(sys.argv) > 2 else "./traces/tvla_regions.zarr"
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "./result"
        threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 4.5
        run_analysis(zarr_path, output_dir, threshold)
    elif command == "verify":
        zarr_path = sys.argv[2] if len(sys.argv) > 2 else "./traces/tvla_regions.zarr"
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 4.5
        passed = verify(zarr_path, threshold)
        sys.exit(0 if passed else 1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()