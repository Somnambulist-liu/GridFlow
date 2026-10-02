"""Generate a synthetic workbook used by the memory/throughput benchmarks.

Usage:  python tools/make_fixture.py [rows] [cols] [out_path]

The generated sheet mimics a real report: a text group column, numbers, dates,
and three repeated fill/font styles so that style handling is exercised.
"""
import os
import sys
import time

import openpyxl
from openpyxl.styles import Font, PatternFill

import bench_common  # noqa: F401  (path bootstrap)

ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
COLS = int(sys.argv[2]) if len(sys.argv) > 2 else 15
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
    bench_common.ROOT, "test_output", "fixture.xlsx"
)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    t0 = time.perf_counter()

    headers = ["区域", "部门", "产品", "数量", "单价", "金额", "日期",
               "负责人", "备注", "状态", "等级", "仓库", "渠道", "客户", "评分"][:COLS]
    styles = [
        (PatternFill("solid", fgColor="FFF2CC"), Font(bold=False)),
        (PatternFill("solid", fgColor="E2EFDA"), Font(bold=False)),
        (None, None),
    ]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(headers)
    for row_idx in range(1, ROWS + 1):
        fill, font = styles[row_idx % 3]
        values = []
        for col in range(1, COLS + 1):
            if col == 1:
                values.append(f"区域{row_idx % 50:02d}")
            elif col == 2:
                values.append(f"部门{row_idx % 12}")
            elif col == 3:
                values.append(f"产品{row_idx % 200}")
            elif col in (4, 5, 15):
                values.append((row_idx * col) % 1000)
            elif col == 6:
                values.append(f"=D{row_idx + 1}*E{row_idx + 1}")
            else:
                values.append(f"值{row_idx}-{col}")
        for col_idx, value in enumerate(values, 1):
            cell = ws.cell(row=row_idx + 1, column=col_idx, value=value)
            if fill is not None:
                cell.fill = fill
            if font is not None:
                cell.font = font
        if row_idx % 5000 == 0:
            print(f"  ... {row_idx} rows")

    wb.save(OUT)
    wb.close()
    size_mb = os.path.getsize(OUT) / 1048576
    print(f"fixture: {OUT}")
    print(f"  {ROWS} rows x {COLS} cols, {size_mb:.1f} MB, "
          f"built in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
