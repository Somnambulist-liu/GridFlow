"""Measure peak memory + wall time of every GridFlow processing worker.

Each scenario runs in its own fresh process (memory peak is process-lifetime),
so the driver re-executes this script with ``--scenario NAME``.

Usage:
    python tools/make_fixture.py 20000 15        # once, creates the fixture
    python tools/bench_memory.py --all
    python tools/bench_memory.py --scenario split
    # A/B against a different copy of core/ (e.g. the pre-change modules):
    python tools/bench_memory.py --all --core-dir test_output/oldver --tag old
"""
import gc
import json
import os
import subprocess
import sys
import time

import bench_common as bc

if "--core-dir" in sys.argv:
    _core_dir = sys.argv[sys.argv.index("--core-dir") + 1]
    if not os.path.isabs(_core_dir):
        _core_dir = os.path.join(bc.ROOT, _core_dir)
    sys.path.insert(0, _core_dir)
    print(f"core modules from: {_core_dir}")

TAG = "new"
if "--tag" in sys.argv:
    TAG = sys.argv[sys.argv.index("--tag") + 1]

FIXTURE = os.environ.get("BENCH_FIXTURE", os.path.join(bc.ROOT, "test_output", "fixture.xlsx"))
MERGE_PREFIX = os.environ.get("BENCH_MERGE_PREFIX", os.path.join(bc.ROOT, "test_output", "merge_part"))
CSV_FIXTURE = os.environ.get("BENCH_CSV", os.path.join(bc.ROOT, "test_output", "fixture.csv"))
OUT_DIR = os.path.join(bc.ROOT, "test_output", "bench")
CSV_ROWS = 20000
SHEET = "Data"
HEADERS = ["区域", "部门", "产品", "数量", "单价", "金额", "日期",
           "负责人", "备注", "状态", "等级", "仓库", "渠道", "客户", "评分"]


def ensure_csv_fixture() -> str:
    """Create the CSV fixture used by the convert scenario (once)."""
    if os.path.exists(CSV_FIXTURE):
        return CSV_FIXTURE
    import csv
    os.makedirs(os.path.dirname(CSV_FIXTURE), exist_ok=True)
    with open(CSV_FIXTURE, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADERS)
        for i in range(CSV_ROWS):
            writer.writerow([f"区域{i % 50:02d}", f"部门{i % 12}", f"产品{i % 200}",
                             (i * 4) % 1000, (i * 5) % 1000, (i * 6) % 1000,
                             f"2026-01-{(i % 28) + 1:02d}", f"负责人{i % 30}",
                             f"备注{i}", "已完成" if i % 2 else "待处理",
                             f"L{i % 5}", f"仓库{i % 4}", f"渠道{i % 3}",
                             f"客户{i % 100}", (i % 5) + 1])
    return CSV_FIXTURE


def _run_worker(worker, configure):
    """Run a QThread worker body synchronously and report its outcome."""
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance() or QCoreApplication([])
    result = {"ok": False, "message": ""}

    worker.finished.connect(lambda msg: result.update(ok=True, message=msg))
    worker.error_occurred.connect(lambda msg: result.update(ok=False, message=msg))
    configure(worker)
    worker.run()  # direct call: no event loop needed
    del app
    return result


def scenario_split():
    from core.splitter import SplitWorker

    def configure(worker):
        worker.configure(
            file_path=FIXTURE, sheet_name=SHEET, column="区域",
            mode="files", output_dir=OUT_DIR,
            output_path=os.path.join(OUT_DIR, "split_sheets.xlsx"),
        )

    return _run_worker(SplitWorker(), configure)


def scenario_merge(n_files=3):
    from core.merger import MergeWorker
    paths = [f"{MERGE_PREFIX}{i}.xlsx" for i in range(1, n_files + 1)]

    def configure(worker):
        worker.configure(mode="files", file_paths=paths, output_dir=OUT_DIR,
                         output_name="merged.xlsx")

    return _run_worker(MergeWorker(), configure)


def scenario_dedup():
    from core.deduper import DedupWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         columns=["区域", "部门"], keep="first",
                         output_dir=OUT_DIR)

    return _run_worker(DedupWorker(), configure)


def scenario_filter():
    from core.filter_engine import FilterWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         conditions=[{"column": "数量", "operator": "gt", "value": 500}],
                         logic="AND", output_dir=OUT_DIR, output_name="filtered.xlsx")

    return _run_worker(FilterWorker(), configure)


def scenario_pivot():
    from core.pivoter import PivotWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         row_field="区域", col_field="部门", value_field="评分",
                         agg_func="count", output_dir=OUT_DIR,
                         output_name="pivot.xlsx")

    return _run_worker(PivotWorker(), configure)


def scenario_columns():
    from core.column_ops import ColumnOpsWorker
    kept = ["区域", "部门", "产品", "数量", "单价"]

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET, kept_columns=kept,
                         renames={"数量": "数量2"}, order=kept, calc_columns=[],
                         output_dir=OUT_DIR, output_name="columns.xlsx")

    return _run_worker(ColumnOpsWorker(), configure)


def scenario_validate():
    from core.validator import ValidateWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         checks={"empty": True}, output_dir=OUT_DIR)

    return _run_worker(ValidateWorker(), configure)


def scenario_convert():
    from core.converter import ConvertWorker

    csv_path = ensure_csv_fixture()

    def configure(worker):
        worker.configure(file_paths=[csv_path], target_format="xlsx", output_dir=OUT_DIR)

    return _run_worker(ConvertWorker(), configure)


# ── 覆盖率补充：这些分支在原基准里没被跑到 ──────────────────────────

HEADER_ONLY = os.path.join(bc.ROOT, "test_output", "header_only.xlsx")
EMPTY_XLSX = os.path.join(bc.ROOT, "test_output", "empty.xlsx")


def ensure_edge_fixtures():
    """只有表头的表 + 完全空白的表。"""
    if not os.path.exists(HEADER_ONLY):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = SHEET
        ws.append(HEADERS)
        wb.save(HEADER_ONLY)
        wb.close()
    if not os.path.exists(EMPTY_XLSX):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.active.title = SHEET
        wb.save(EMPTY_XLSX)
        wb.close()


def scenario_dedup_last():
    from core.deduper import DedupWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         columns=["区域", "部门"], keep="last", output_dir=OUT_DIR)

    return _run_worker(DedupWorker(), configure)


def scenario_filter_none():
    from core.filter_engine import FilterWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         conditions=[{"column": "数量", "operator": "gt", "value": 10 ** 9}],
                         logic="AND", output_dir=OUT_DIR, output_name="filtered_none.xlsx")

    return _run_worker(FilterWorker(), configure)


def scenario_pivot_header_only():
    from core.pivoter import PivotWorker
    ensure_edge_fixtures()

    def configure(worker):
        worker.configure(file_path=HEADER_ONLY, sheet_name=SHEET,
                         row_field="区域", col_field="部门", value_field="评分",
                         agg_func="count", output_dir=OUT_DIR, output_name="pivot_empty.xlsx")

    return _run_worker(PivotWorker(), configure)


def scenario_pivot_bad_field():
    from core.pivoter import PivotWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         row_field="区域", col_field="部门", value_field="不存在的列",
                         agg_func="sum", output_dir=OUT_DIR, output_name="pivot_bad.xlsx")

    return _run_worker(PivotWorker(), configure)


def scenario_columns_calc():
    from core.column_ops import ColumnOpsWorker
    kept = ["区域", "部门", "数量", "单价"]

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET, kept_columns=kept,
                         renames={"数量": "数量"}, order=kept,
                         calc_columns=[{"name": "金额", "expression": "{数量} * {单价}"},
                                       {"name": "混合", "expression": "{数量} + 备注"}],
                         output_dir=OUT_DIR, output_name="columns_calc.xlsx")

    return _run_worker(ColumnOpsWorker(), configure)


def scenario_validate_full():
    from core.validator import ValidateWorker

    def configure(worker):
        worker.configure(file_path=FIXTURE, sheet_name=SHEET,
                         checks={"empty": True, "empty_threshold": 1,
                                 "outliers": True, "outlier_multiplier": 1.5,
                                 "type_check": True, "duplicates": True},
                         output_dir=OUT_DIR)

    return _run_worker(ValidateWorker(), configure)


def scenario_validate_empty():
    from core.validator import ValidateWorker
    ensure_edge_fixtures()

    def configure(worker):
        worker.configure(file_path=HEADER_ONLY, sheet_name=SHEET,
                         checks={"empty": True, "duplicates": True}, output_dir=OUT_DIR)

    return _run_worker(ValidateWorker(), configure)


def scenario_merge_with_empty():
    from core.merger import MergeWorker
    ensure_edge_fixtures()
    paths = [f"{MERGE_PREFIX}1.xlsx", EMPTY_XLSX, f"{MERGE_PREFIX}2.xlsx"]

    def configure(worker):
        worker.configure(mode="files", file_paths=paths, output_dir=OUT_DIR,
                         output_name="merged_with_empty.xlsx")

    return _run_worker(MergeWorker(), configure)


SCENARIOS = {
    "split": scenario_split,
    "merge": scenario_merge,
    "dedup": scenario_dedup,
    "filter": scenario_filter,
    "pivot": scenario_pivot,
    "columns": scenario_columns,
    "validate": scenario_validate,
    "convert": scenario_convert,
    "dedup_last": scenario_dedup_last,
    "filter_none": scenario_filter_none,
    "pivot_header_only": scenario_pivot_header_only,
    "pivot_bad_field": scenario_pivot_bad_field,
    "columns_calc": scenario_columns_calc,
    "validate_full": scenario_validate_full,
    "validate_empty": scenario_validate_empty,
    "merge_with_empty": scenario_merge_with_empty,
}


def run_one(name: str):
    os.makedirs(OUT_DIR, exist_ok=True)
    baseline_mb = bc.memory_mb()[1]
    gc.collect()
    t0 = time.perf_counter()
    try:
        result = SCENARIOS[name]()
    except Exception as exc:  # keep the driver alive
        result = {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
    seconds = time.perf_counter() - t0
    peak_mb, current_mb = bc.memory_mb()
    payload = {
        "scenario": name,
        "tag": TAG,
        "seconds": round(seconds, 2),
        "baseline_mb": round(baseline_mb, 1),
        "peak_mb": round(peak_mb, 1),
        "current_mb": round(current_mb, 1),
        "ok": result.get("ok"),
        "message": str(result.get("message"))[:120],
    }
    print("@@RESULT@@" + json.dumps(payload))


def _child_args(name: str) -> list:
    """Rebuild this command line for the child process (keeps --core-dir / --tag)."""
    args = [sys.executable, os.path.abspath(__file__), "--scenario", name]
    for flag in ("--core-dir", "--tag"):
        if flag in sys.argv:
            args += [flag, sys.argv[sys.argv.index(flag) + 1]]
    return args


def _positional_names(argv) -> list:
    """Positional scenario names, skipping flags and their values."""
    flags_with_value = {"--core-dir", "--tag", "--scenario"}
    names, skip = [], False
    for arg in argv:
        if skip:
            skip = False
            continue
        if arg in flags_with_value:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        names.append(arg)
    return [n for n in names if n in SCENARIOS]


def run_all():
    names = _positional_names(sys.argv[1:]) or list(SCENARIOS)
    rows = []
    for name in names:
        proc = subprocess.run(
            _child_args(name),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=bc.ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        payload = None
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        for line in stdout.splitlines():
            if line.startswith("@@RESULT@@"):
                payload = json.loads(line[len("@@RESULT@@"):])
        if payload is None:
            payload = {"scenario": name, "ok": False,
                       "message": (stdout + stderr).strip()[-200:]}
        rows.append(payload)
        print(f"{name:<10} {payload.get('seconds', 0):>7}s  "
              f"peak {payload.get('peak_mb', 0):>7} MB  "
              f"({payload.get('message', '')})")

    print()
    out = os.path.join(bc.ROOT, "test_output", "bench", f"results_{TAG}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(f"results -> {out}")
    print()
    print(f"{'scenario':<10} {'sec':>8} {'baseline':>10} {'peak':>10} {'delta':>10}  ok")
    for row in rows:
        delta = row.get("peak_mb", 0) - row.get("baseline_mb", 0)
        print(f"{row['scenario']:<10} {row.get('seconds', 0):>8} "
              f"{row.get('baseline_mb', 0):>10} {row.get('peak_mb', 0):>10} "
              f"{delta:>10.1f}  {row.get('ok')}")


if __name__ == "__main__":
    if "--scenario" in sys.argv:
        run_one(sys.argv[sys.argv.index("--scenario") + 1])
    else:
        run_all()
