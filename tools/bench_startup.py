"""Measure GridFlow cold-start cost.

Two phases in one fresh process:

1. ``import main``   — module import graph (PySide6, every feature, openpyxl...)
2. ``main.main()``   — QApplication + MainWindow + feature construction + first paint

The Qt platform is forced to ``offscreen`` so the numbers are reproducible on
headless machines. Absolute timings on a real desktop are larger, but the
before/after delta is what this script is for.

Usage:  python tools/bench_startup.py [--json]
"""
import json
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import bench_common as bc  # noqa: E402  (path bootstrapping happens inside)

timings = {}

# ── phase 1: import graph ────────────────────────────────────────────
with bc.Timer(timings, "import main (all modules)"):
    import main as app_main  # noqa: F401

# ── phase 2: application start-up ────────────────────────────────────
from PySide6.QtWidgets import QApplication  # noqa: E402

t_phase2 = time.perf_counter()


def fake_exec(self):  # stop right after the window is shown
    timings["show() -> exec() called"] = time.perf_counter() - t_phase2
    return 0


QApplication.exec = fake_exec

try:
    app_main.main()
except SystemExit:
    pass

peak_mb, current_mb = bc.memory_mb()
if "--json" in sys.argv:
    print(json.dumps({"timings": timings, "peak_mb": peak_mb, "current_mb": current_mb}))
else:
    bc.report("startup", timings, peak_mb, current_mb)
    print(f"  python {sys.version.split()[0]}  PySide6 {__import__('PySide6').__version__}")
