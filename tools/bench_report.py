"""Render the before/after benchmark table from the recorded JSON results.

    python tools/bench_report.py results_old.json results_new_final.json
"""
import json
import os
import sys

import bench_common as bc

ORDER = ["split", "merge", "dedup", "filter", "columns", "pivot", "validate", "convert"]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return {row["scenario"]: row for row in json.load(fh)}


def main():
    bench_dir = os.path.join(bc.ROOT, "test_output", "bench")
    old_name = sys.argv[1] if len(sys.argv) > 1 else "results_old.json"
    new_name = sys.argv[2] if len(sys.argv) > 2 else "results_new_final.json"
    old = load(os.path.join(bench_dir, old_name))
    new = load(os.path.join(bench_dir, new_name))

    header = (f"{'scenario':<10} {'sec 前':>8} {'sec 后':>8} "
              f"{'峰值MB 前':>10} {'峰值MB 后':>10} {'内存降幅':>9}")
    print(header)
    print("-" * 70)
    for key in ORDER:
        o, n = old.get(key), new.get(key)
        if not o or not n:
            continue
        drop = f"{(1 - n['peak_mb'] / o['peak_mb']) * 100:.0f}%"
        print(f"{key:<10} {o['seconds']:>8} {n['seconds']:>8} "
              f"{o['peak_mb']:>10} {n['peak_mb']:>10} {drop:>9}")


if __name__ == "__main__":
    main()
