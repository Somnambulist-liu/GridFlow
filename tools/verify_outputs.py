"""Capture a canonical digest of what every GridFlow worker produces.

The digests are the safety net for the performance work: run this before and
after an optimisation and compare the two output trees. Values, styles,
merged ranges, column widths and row heights are all part of the digest.

Usage:
    python tools/verify_outputs.py --out test_output/verify/before
    python tools/verify_outputs.py --out test_output/verify/after
    python tools/verify_outputs.py --compare test_output/verify/before test_output/verify/after
"""
import difflib
import hashlib
import json
import os
import shutil
import sys

import openpyxl

import bench_common as bc
import bench_memory as bm

if "--core-dir" in sys.argv:
    _core_dir = sys.argv[sys.argv.index("--core-dir") + 1]
    if not os.path.isabs(_core_dir):
        _core_dir = os.path.join(bc.ROOT, _core_dir)
    sys.path.insert(0, _core_dir)
    print(f"core modules from: {_core_dir}")


def cell_repr(cell) -> str:
    if not cell.has_style:
        return f"{cell.value!r}"
    font = cell.font
    fill = cell.fill
    border = cell.border
    align = cell.alignment
    style = "|".join([
        str(font.name), str(font.size), str(font.bold),
        str(font.color.rgb) if font.color is not None else "-",
        str(fill.patternType),
        str(fill.fgColor.rgb) if fill.fgColor is not None else "-",
        str(border.left.style), str(border.right.style),
        str(border.top.style), str(border.bottom.style),
        str(align.horizontal), str(align.vertical), str(align.wrap_text),
        str(cell.number_format),
    ])
    return f"{cell.value!r}~{style}"


def digest_workbook(path: str) -> list:
    lines = []
    wb = openpyxl.load_workbook(path, data_only=False)
    for ws in wb.worksheets:
        lines.append(f"[sheet] {ws.title} dims={ws.max_row}x{ws.max_column}")
        for letter, dim in sorted(ws.column_dimensions.items()):
            if dim.width is not None:
                lines.append(f"[colwidth] {ws.title} {letter}={dim.width}")
        for row_idx, dim in sorted(ws.row_dimensions.items()):
            if dim.height is not None:
                lines.append(f"[rowheight] {ws.title} {row_idx}={dim.height}")
        for rng in sorted(str(r) for r in ws.merged_cells.ranges):
            lines.append(f"[merge] {ws.title} {rng}")
        for row_idx, row in enumerate(ws.iter_rows(), 1):
            lines.append(
                f"[row] {ws.title} {row_idx} " + "\t".join(cell_repr(c) for c in row)
            )
    wb.close()
    return lines


def digest_dir(path: str) -> dict:
    entries = {}
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if not os.path.isfile(full) or not name.lower().endswith((".xlsx", ".csv")):
            continue
        lines = digest_workbook(full) if name.lower().endswith(".xlsx") else \
            open(full, encoding="utf-8", errors="replace").read().splitlines()
        blob = "\n".join(lines).encode("utf-8")
        entries[name] = {
            "sha256": hashlib.sha256(blob).hexdigest(),
            "lines": len(lines),
        }
        with open(os.path.join(os.path.dirname(path), f"{os.path.basename(path)}.{name}.txt"),
                  "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return entries


def capture(out_root: str, names=None):
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841

    names = names or list(bm.SCENARIOS)
    manifest = {}
    for name in names:
        out_dir = os.path.join(out_root, name)
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        bm.OUT_DIR = out_dir

        result = {"ok": None, "message": ""}
        try:
            res = bm.SCENARIOS[name]()
            result["ok"] = res.get("ok")
            result["message"] = str(res.get("message", ""))
        except Exception as exc:
            result["message"] = f"{type(exc).__name__}: {exc}"
            result["ok"] = False

        manifest[name] = {
            "result": result,
            "files": digest_dir(out_dir),
        }
        print(f"  {name:<10} ok={result['ok']} files={len(manifest[name]['files'])} "
              f"msg={result['message'][:60]!r}")

    os.makedirs(out_root, exist_ok=True)
    manifest_path = os.path.join(out_root, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"manifest -> {manifest_path}")
    return manifest


def compare(before_root: str, after_root: str) -> int:
    with open(os.path.join(before_root, "manifest.json"), encoding="utf-8") as fh:
        before = json.load(fh)
    with open(os.path.join(after_root, "manifest.json"), encoding="utf-8") as fh:
        after = json.load(fh)

    problems = 0
    for name in sorted(set(before) | set(after)):
        b = before.get(name)
        a = after.get(name)
        if b is None or a is None:
            print(f"[MISSING] {name}")
            problems += 1
            continue
        if b["files"].keys() != a["files"].keys():
            print(f"[FILES ] {name}: file set differs")
            print("   only before:", sorted(set(b['files']) - set(a['files']))[:10])
            print("   only after :", sorted(set(a['files']) - set(b['files']))[:10])
            problems += 1
        diffs = [f for f in b["files"] if f in a["files"]
                 and b["files"][f]["sha256"] != a["files"][f]["sha256"]]
        if diffs:
            problems += 1
            print(f"[DIFF  ] {name}: {len(diffs)} file(s) differ -> {diffs[:6]}")
            for d in diffs[:2]:
                bf = os.path.join(before_root, f"{name}.{d}.txt")
                af = os.path.join(after_root, f"{name}.{d}.txt")
                if os.path.exists(bf) and os.path.exists(af):
                    bl = open(bf, encoding="utf-8").read().splitlines()
                    al = open(af, encoding="utf-8").read().splitlines()
                    shown = 0
                    for line in difflib.unified_diff(bl, al, "before", "after", lineterm="", n=0):
                        print("   ", line[:200])
                        shown += 1
                        if shown > 12:
                            break
        if b["result"]["message"] != a["result"]["message"]:
            print(f"[MSG   ] {name}: message differs")
            print("    before:", b["result"]["message"][:160])
            print("    after :", a["result"]["message"][:160])
    print()
    if problems:
        print(f"RESULT: {problems} scenario(s) differ")
    else:
        print("RESULT: all scenarios byte-identical")
    return 1 if problems else 0


if __name__ == "__main__":
    if "--compare" in sys.argv:
        idx = sys.argv.index("--compare")
        sys.exit(compare(sys.argv[idx + 1], sys.argv[idx + 2]))
    out_root = os.path.join(bc.ROOT, "test_output", "verify", "current")
    if "--out" in sys.argv:
        out_root = sys.argv[sys.argv.index("--out") + 1]
        if not os.path.isabs(out_root):
            out_root = os.path.join(bc.ROOT, out_root)
    names = None
    if "--only" in sys.argv:
        names = sys.argv[sys.argv.index("--only") + 1].split(",")
    print(f"capturing -> {out_root}")
    capture(out_root, names)
