"""A/B the tricky split paths against the pre-optimisation implementation.

Covers what the standard benchmark does not: a multi-row header, leading rows,
trailing rows, merged cells, formula-preserving mode and the multi-sheet mode.

    # current code
    python tools/edge_scenarios.py --out test_output/edge/new

    # pre-change code, checked out under test_output/oldver
    python tools/edge_scenarios.py --core-dir test_output/oldver --out test_output/edge/old

    python tools/edge_scenarios.py --compare test_output/edge/old test_output/edge/new
"""
import hashlib
import json
import os
import shutil
import sys

import bench_common as bc  # bootstraps sys.path with the repo root

if "--core-dir" in sys.argv:
    core_dir = sys.argv[sys.argv.index("--core-dir") + 1]
    if not os.path.isabs(core_dir):
        core_dir = os.path.join(bc.ROOT, core_dir)
    sys.path.insert(0, core_dir)
    print(f"core modules from: {core_dir}")

import openpyxl  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402

from core.splitter import SplitWorker  # noqa: E402

DATA_ROWS = 400
TAIL_FIRST = DATA_ROWS + 4      # 1-based sheet row of the first footer row
TAIL_LAST = DATA_ROWS + 5


def build_fixture(path: str):
    """Sheet layout: 2 leading rows, header on row 3, data, 2 trailing rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"

    title_font = Font(bold=True, size=14, color="FF1F4E79")
    ws["A1"] = "2026 年度销售报表"
    ws["A1"].font = title_font
    ws.merge_cells("A1:E1")
    ws["A2"] = "生成时间：2026-10-03"
    ws["A2"].font = Font(italic=True, color="FF808080")

    headers = ["区域", "部门", "产品", "数量", "金额"]
    header_fill = PatternFill("solid", fgColor="FFDDEBF7")
    for idx, name in enumerate(headers, 1):
        cell = ws.cell(row=3, column=idx, value=name)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    body_fills = [PatternFill("solid", fgColor="FFFFF2CC"),
                  PatternFill("solid", fgColor="FFE2EFDA"),
                  None]
    for i in range(DATA_ROWS):
        sheet_row = 4 + i
        region = f"区域{i % 7:02d}"
        values = [region, f"部门{i % 5}", f"产品{i % 50}",
                  (i % 90) + 10, None]
        for col_idx, value in enumerate(values, 1):
            cell = ws.cell(row=sheet_row, column=col_idx, value=value)
            fill = body_fills[i % 3]
            if fill is not None:
                cell.fill = fill
        amount = ws.cell(row=sheet_row, column=5, value=f"=D{sheet_row}*2")
        amount.number_format = "0.00"

    ws.cell(row=TAIL_FIRST, column=1, value="合计")
    ws.cell(row=TAIL_FIRST, column=4, value=f"=SUM(D4:D{DATA_ROWS + 3})")
    # 可平移的相对引用：用来验证公式模式下“尾部行”是否也做坐标翻译
    ws.cell(row=TAIL_FIRST, column=5, value=f"=D{TAIL_FIRST}*2")
    ws.cell(row=TAIL_LAST, column=1, value="备注：数据仅供演示")
    ws.merge_cells(start_row=TAIL_LAST, start_column=1, end_row=TAIL_LAST, end_column=3)

    ws.column_dimensions["A"].width = 14.5
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["E"].width = 18.25
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[3].height = 22

    wb.save(path)
    wb.close()


CONFIGS = {
    # name: configure() kwargs
    "files_lead_tail": dict(
        mode="files", column="区域", preserve_formulas=False,
        header_row=3, include_lead_rows=True,
        include_tail_rows=True, tail_rows_start=TAIL_FIRST, tail_rows_end=TAIL_LAST,
    ),
    "sheets_lead_tail": dict(
        mode="sheets", column="区域", preserve_formulas=False,
        header_row=3, include_lead_rows=True,
        include_tail_rows=True, tail_rows_start=TAIL_FIRST, tail_rows_end=TAIL_LAST,
    ),
    "files_formulas": dict(
        mode="files", column="区域", preserve_formulas=True,
        header_row=3, include_lead_rows=True,
        include_tail_rows=True, tail_rows_start=TAIL_FIRST, tail_rows_end=TAIL_LAST,
    ),
    "sheets_formulas_lead_tail": dict(
        mode="sheets", column="部门", preserve_formulas=True,
        header_row=3, include_lead_rows=True,
        include_tail_rows=True, tail_rows_start=TAIL_FIRST, tail_rows_end=TAIL_LAST,
    ),
    "files_no_lead": dict(
        mode="files", column="部门", preserve_formulas=False,
        header_row=3, include_lead_rows=False,
    ),
}


def run_config(name, kwargs, fixture, out_dir):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    worker = SplitWorker()
    result = {"ok": False, "message": ""}
    worker.finished.connect(lambda msg: result.update(ok=True, message=msg))
    worker.error_occurred.connect(lambda msg: result.update(ok=False, message=msg))
    worker.configure(
        file_path=fixture, sheet_name="Data",
        output_dir=out_dir,
        output_path=os.path.join(out_dir, "combined.xlsx"),
        **kwargs,
    )
    worker.run()
    return result


def digest_dir_light(path):
    """Digest that keeps memory sane for 400-row x 7-region outputs."""
    from verify_outputs import digest_workbook
    entries = {}
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if not os.path.isfile(full) or not name.lower().endswith(".xlsx"):
            continue
        lines = digest_workbook(full)
        blob = "\n".join(lines).encode("utf-8")
        entries[name] = hashlib.sha256(blob).hexdigest()
        with open(os.path.join(os.path.dirname(path), f"{os.path.basename(path)}.{name}.txt"),
                  "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return entries


def capture(out_root):
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication([])

    fixture = os.path.join(bc.ROOT, "test_output", "edge_fixture.xlsx")
    build_fixture(fixture)

    manifest = {}
    for name, kwargs in CONFIGS.items():
        out_dir = os.path.join(out_root, name)
        result = run_config(name, kwargs, fixture, out_dir)
        manifest[name] = {"result": result, "files": digest_dir_light(out_dir)}
        print(f"  {name:<26} ok={result['ok']} files={len(manifest[name]['files'])} "
              f"msg={result['message'][:50]!r}")

    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"manifest -> {os.path.join(out_root, 'manifest.json')}")


def compare(old_root, new_root):
    old = json.load(open(os.path.join(old_root, "manifest.json"), encoding="utf-8"))
    new = json.load(open(os.path.join(new_root, "manifest.json"), encoding="utf-8"))
    problems = 0
    for name in sorted(set(old) | set(new)):
        o, n = old.get(name), new.get(name)
        if not o or not n:
            print(f"[MISSING] {name}")
            problems += 1
            continue
        if o["result"] != n["result"]:
            print(f"[MSG    ] {name}: {o['result']} != {n['result']}")
            problems += 1
        if set(o["files"]) != set(n["files"]):
            print(f"[FILES  ] {name}: {sorted(set(o['files']) ^ set(n['files']))[:8]}")
            problems += 1
            continue
        diff = [f for f in o["files"] if o["files"][f] != n["files"][f]]
        if diff:
            print(f"[DIFF   ] {name}: {len(diff)} file(s) -> {diff[:5]}")
            problems += 1
    print()
    print("RESULT:", "all edge scenarios identical" if not problems
          else f"{problems} difference(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    if "--compare" in sys.argv:
        idx = sys.argv.index("--compare")
        sys.exit(compare(sys.argv[idx + 1], sys.argv[idx + 2]))
    out_root = os.path.join(bc.ROOT, "test_output", "edge", "current")
    if "--out" in sys.argv:
        out_root = sys.argv[sys.argv.index("--out") + 1]
        if not os.path.isabs(out_root):
            out_root = os.path.join(bc.ROOT, out_root)
    print(f"capturing -> {out_root}")
    capture(out_root)
