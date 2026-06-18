import openpyxl
from copy import copy
from typing import List, Dict


def _extract_cell_style(cell):
    """从源单元格提取样式信息（Font、Fill、Border、Alignment、number_format）。

    使用 copy.copy() 深拷贝样式对象，确保关闭源工作簿后样式仍然可用。
    对空单元格或无样式的单元格返回 None。
    """
    if cell is None or not cell.has_style:
        return None
    return {
        "font": copy(cell.font),
        "fill": copy(cell.fill),
        "border": copy(cell.border),
        "alignment": copy(cell.alignment),
        "number_format": cell.number_format,
    }


def _apply_style_to_cell(dst_cell, style):
    """将提取的样式字典应用到目标单元格。"""
    if style is None:
        return
    if style.get("font") is not None:
        dst_cell.font = style["font"]
    if style.get("fill") is not None:
        dst_cell.fill = style["fill"]
    if style.get("border") is not None:
        dst_cell.border = style["border"]
    if style.get("alignment") is not None:
        dst_cell.alignment = style["alignment"]
    if style.get("number_format") is not None and style["number_format"] != "General":
        dst_cell.number_format = style["number_format"]


def _extract_row_styles(row_cells):
    """从一行 Cell 对象中提取所有单元格的样式信息。"""
    return [_extract_cell_style(c) for c in row_cells]


def _copy_column_widths(src_ws, dst_ws):
    """从源工作表复制列宽到目标工作表。"""
    for col_letter, col_dim in src_ws.column_dimensions.items():
        if col_dim.width is not None:
            dst_ws.column_dimensions[col_letter].width = col_dim.width


def _copy_row_heights(src_ws, dst_ws, row_map):
    """根据行号映射复制行高。

    Args:
        src_ws: 源工作表
        dst_ws: 目标工作表
        row_map: {src_row: dst_row} 映射表
    """
    for src_row, dst_row in row_map.items():
        src_dim = src_ws.row_dimensions.get(src_row)
        if src_dim is not None and src_dim.height is not None:
            dst_ws.row_dimensions[dst_row].height = src_dim.height


def read_sheet_grouped_with_styles(
    file_path: str,
    sheet_name: str,
    column: str,
    data_only: bool = True,
) -> tuple:
    """以普通模式读取工作表，按列分组，同时保留单元格样式。

    返回 (headers, header_styles, groups)：
    - headers: 表头值列表
    - header_styles: 表头样式列表（每个元素为样式字典或 None）
    - groups: {value: [(src_row, row_values, row_styles), ...]}
      其中 row_values 为值列表，row_styles 为样式字典列表
    """
    wb = openpyxl.load_workbook(file_path, data_only=data_only)
    ws = wb[sheet_name]

    all_rows = list(ws.iter_rows())
    if not all_rows:
        wb.close()
        return [], [], {}

    header_cells = all_rows[0]
    headers = [c.value for c in header_cells]
    header_styles = _extract_row_styles(header_cells)

    headers_str = [str(h) if h is not None else f"Col{i}" for i, h in enumerate(headers)]
    if column not in headers_str:
        wb.close()
        return headers, header_styles, {}

    col_idx = headers_str.index(column)

    groups: Dict[str, list] = {}
    for src_row, row_cells in enumerate(all_rows[1:], start=2):
        key = row_cells[col_idx].value if col_idx < len(row_cells) else None
        key = "(空)" if key is None else str(key)
        row_values = [c.value for c in row_cells]
        row_styles = _extract_row_styles(row_cells)
        groups.setdefault(key, []).append((src_row, row_values, row_styles))

    wb.close()
    return headers, header_styles, groups


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
