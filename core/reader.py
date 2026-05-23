import openpyxl
from typing import List, Dict


def get_sheet_names(file_path: str) -> List[str]:
    wb = openpyxl.load_workbook(file_path, read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


def get_columns(file_path: str, sheet_name: str) -> List[str]:
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb[sheet_name]
    row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    wb.close()
    return [str(c) for c in row if c is not None]


def get_unique_values(file_path: str, sheet_name: str, column: str) -> Dict[str, int]:
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb[sheet_name]
    headers = [str(c) for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    if column not in headers:
        wb.close()
        return {}
    col_idx = headers.index(column)
    counts: Dict[str, int] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if col_idx < len(row):
            val = row[col_idx]
            val = "(空)" if val is None else str(val)
        else:
            val = "(空)"
        counts[val] = counts.get(val, 0) + 1
    wb.close()
    return counts


def read_sheet_grouped(
    file_path: str,
    sheet_name: str,
    column: str,
) -> tuple:
    """流式读取并按列分组，返回 (headers, {value: [row_tuple, ...]})"""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    row_iter = ws.iter_rows(values_only=True)

    try:
        header_row = next(row_iter)
    except StopIteration:
        wb.close()
        return [], {}

    headers = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(header_row)]
    if column not in headers:
        wb.close()
        return headers, {}
    col_idx = headers.index(column)

    groups: Dict[str, list] = {}
    for row in row_iter:
        key = row[col_idx] if col_idx < len(row) else None
        key = "(空)" if key is None else str(key)
        groups.setdefault(key, []).append(tuple(row))

    wb.close()
    return headers, groups
