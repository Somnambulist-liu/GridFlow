"""Excel 读取与样式复制工具。

本模块是拆分功能（core.splitter）的地基，因此对性能敏感：

* 源工作簿在一次读取中只解析一次，同时取出值、样式、列宽、行高、合并区域
  （``SheetLayout``），拆分时不必为了列宽/行高再打开一遍源文件。
* 单元格样式按“样式指纹”去重（``StyleTable``）。旧实现为每个单元格复制
  Font/Fill/Border/Alignment 各一份，30 万单元格会生成上百万个对象；现在整张表
  只保留几十份样式记录，单元格上只存一个整数 id。
* 逐行流式迭代，不再 ``list(ws.iter_rows())`` 把整张表在内存里再复制一份。
"""
import openpyxl
from copy import copy
from typing import Dict, List, Optional
from openpyxl.utils import get_column_letter as _get_column_letter


# ── 样式表：样式去重 ────────────────────────────────────────────────

class StyleTable:
    """把单元格样式压缩成整数 id。

    openpyxl 的 ``cell._style`` 是一个 ``array('i')``（指向工作簿样式表的索引），
    同一张表里样式相同的单元格其 ``_style`` 完全相同 —— 用它当指纹即可去重。
    每个 id 只在首次出现时复制一次 Font/Fill/Border/Alignment，之后所有单元格
    共享同一条记录。
    """

    __slots__ = ("_ids", "entries", "_row_cache")

    def __init__(self):
        self._ids: Dict[tuple, int] = {}
        # entries[0] 恒为 None，代表“无样式”
        self.entries: List[Optional[dict]] = [None]
        self._row_cache: Dict[tuple, tuple] = {}

    def intern(self, cell) -> int:
        """返回单元格样式的 id；0 表示无样式。"""
        style = cell._style
        if style is None or not any(style):
            return 0
        key = tuple(style)
        sid = self._ids.get(key)
        if sid is None:
            sid = len(self.entries)
            self._ids[key] = sid
            self.entries.append({
                "key": key,
                "font": copy(cell.font),
                "fill": copy(cell.fill),
                "border": copy(cell.border),
                "alignment": copy(cell.alignment),
                "number_format": cell.number_format,
            })
        return sid

    def intern_row(self, cells) -> Optional[tuple]:
        """把一行的样式压缩成 id 元组；整行无样式时返回 None。

        样式模式相同的行共享同一个元组对象（报表里通常只有几种）。
        """
        ids = tuple(self.intern(c) for c in cells)
        if not any(ids):
            return None
        return self._row_cache.setdefault(ids, ids)

    def row_dicts(self, style_row: Optional[tuple]) -> List[Optional[dict]]:
        """兼容旧接口：把 id 元组还原成样式字典列表。"""
        if style_row is None:
            return []
        return [self.entries[sid] if sid else None for sid in style_row]


class StyleApplier:
    """把 ``StyleTable`` 的样式 id 应用到目标工作簿的单元格。

    目标工作簿有自己的字体/填充/边框索引表，源文件的 ``StyleArray`` 不能直接复用。
    这里对每种样式只解析一次目标索引，之后逐格写 ``cell._style``，绕开了 openpyxl
    每次赋值都要做的“按值查重”（旧实现里样式赋值有 3/4 的时间花在查重上）。
    """

    __slots__ = ("_wb", "_cache", "_scratch")

    def __init__(self, workbook):
        self._wb = workbook
        self._cache: Dict[int, object] = {}
        self._scratch = None

    def _scratch_cell(self):
        if self._scratch is None:
            # 借用一张临时工作表解析目标索引，保存前移除
            self._scratch = self._wb.create_sheet("__gf_style_resolver__")
        return self._scratch.cell(row=1, column=1)

    def _resolve(self, style: dict):
        cell = self._scratch_cell()
        # 每次都从“零样式”开始：openpyxl 的样式描述符只覆盖被赋值的字段，
        # 若不复位，上一份样式的 number_format / 对齐等会残留到下一份。
        cell._style = None
        if style.get("font") is not None:
            cell.font = style["font"]
        if style.get("fill") is not None:
            cell.fill = style["fill"]
        if style.get("border") is not None:
            cell.border = style["border"]
        if style.get("alignment") is not None:
            cell.alignment = style["alignment"]
        number_format = style.get("number_format")
        if number_format is not None and number_format != "General":
            cell.number_format = number_format
        return copy(cell._style)

    def apply(self, cell, style_id: int, table: StyleTable) -> None:
        if not style_id:
            return
        array = self._cache.get(style_id)
        if array is None:
            array = self._resolve(table.entries[style_id])
            self._cache[style_id] = array
        cell._style = array

    def close(self) -> None:
        """移除临时工作表；已解析出的样式索引仍指向工作簿的样式集合。"""
        if self._scratch is not None:
            self._wb.remove(self._scratch)
            self._scratch = None


# ── 旧接口（保留给外部调用方） ──────────────────────────────────────

def _extract_cell_style(cell):
    """从源单元格提取样式信息（Font、Fill、Border、Alignment、number_format）。"""
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
    """将提取的样式字典应用到目标单元格（逐格解析，较慢，仅保留兼容）。"""
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
    """根据行号映射复制行高。"""
    for src_row, dst_row in row_map.items():
        src_dim = src_ws.row_dimensions.get(src_row)
        if src_dim is not None and src_dim.height is not None:
            dst_ws.row_dimensions[dst_row].height = src_dim.height


# ── 版式快照（避免二次打开源文件） ──────────────────────────────────

class SheetLayout:
    """源工作表的一次性快照：列宽、行高、合并区域。"""

    __slots__ = ("column_widths", "row_heights", "merged")

    def __init__(self, column_widths: Dict[str, float], row_heights: Dict[int, float],
                 merged: List[tuple]):
        self.column_widths = column_widths
        self.row_heights = row_heights
        self.merged = merged

    @classmethod
    def capture(cls, ws) -> "SheetLayout":
        column_widths = {
            letter: dim.width
            for letter, dim in ws.column_dimensions.items()
            if dim.width is not None
        }
        row_heights = {
            row: dim.height
            for row, dim in ws.row_dimensions.items()
            if dim.height is not None
        }
        merged = [
            (rng.min_col, rng.min_row, rng.max_col, rng.max_row)
            for rng in ws.merged_cells.ranges
        ]
        return cls(column_widths, row_heights, merged)

    def apply_column_widths(self, dst_ws) -> None:
        for letter, width in self.column_widths.items():
            dst_ws.column_dimensions[letter].width = width

    def apply_row_heights(self, dst_ws, row_map: Dict[int, int]) -> None:
        for src_row, dst_row in row_map.items():
            height = self.row_heights.get(src_row)
            if height is not None:
                dst_ws.row_dimensions[dst_row].height = height

    def apply_merged(self, dst_ws, row_map: Dict[int, int]) -> None:
        """按行号映射复制合并区域（仅当起止行都在映射内）。"""
        if not row_map:
            return
        for min_col, min_row, max_col, max_row in self.merged:
            if min_row not in row_map or max_row not in row_map:
                continue
            new_min_row = row_map[min_row]
            new_max_row = row_map[max_row]
            try:
                start_cell = f"{_get_column_letter(min_col)}{new_min_row}"
                end_cell = f"{_get_column_letter(max_col)}{new_max_row}"
                dst_ws.merge_cells(f"{start_cell}:{end_cell}")
            except Exception:
                pass  # 合并区域冲突时静默跳过


# ── write_only 工作簿的临时文件清理 ─────────────────────────────────

def discard_write_only_workbook(workbook) -> None:
    """放弃一个 write_only 工作簿时，顺手删掉它的临时文件。

    openpyxl 的 write_only 工作表把行写进 %TEMP% 的临时文件，只有 ``save()`` 或
    ``writer.cleanup()`` 才会删除；直接丢弃要等进程退出（openpyxl 用 atexit 兜底，
    而 Windows 上文件句柄没释放时连 atexit 也删不掉）。

    注意顺序：必须先 ``ws.close()`` 收好 XML 流、释放文件句柄，``cleanup()`` 里的
    ``os.remove`` 才会成功。
    """
    if workbook is None:
        return
    for sheet in list(getattr(workbook, "_sheets", None) or []):
        writer = getattr(sheet, "_writer", None)
        if writer is None:
            continue
        try:
            if not getattr(sheet, "closed", False):
                sheet.close()
        except Exception:
            pass
        try:
            writer.cleanup()
        except Exception:
            pass


class StreamedWorkbook:
    """托管 write_only 工作簿的临时文件生命周期。

    只有显式 ``save()`` 成功才保留产物；中途抛错、取消、或者本来就决定不输出
    （没有重复行 / 没有匹配行 / 没有读取到数据）时，一律连临时文件一起清掉::

        with StreamedWorkbook() as out:
            ws = out.sheet()
            ...
            out.save(path)
    """

    __slots__ = ("wb", "_saved")

    def __init__(self):
        self.wb = openpyxl.Workbook(write_only=True)
        self._saved = False

    def sheet(self, title=None):
        if title is None:
            return self.wb.create_sheet()
        return self.wb.create_sheet(title=title)

    def save(self, path: str) -> None:
        self.wb.save(path)
        self.wb.close()
        self._saved = True

    def discard(self) -> None:
        discard_write_only_workbook(self.wb)
        self._saved = True          # 已清理，__exit__ 不必再处理

    def __enter__(self) -> "StreamedWorkbook":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if not self._saved:
            discard_write_only_workbook(self.wb)
        return False


# ── 核心读取：一次遍历取全部数据 ────────────────────────────────────

class ReadResult:
    """``read_grouped_data`` 的返回值容器。"""

    __slots__ = ("headers", "header_style_row", "header_cells", "groups", "leading",
                 "tail", "styles", "layout", "row_count", "column_index")

    def __init__(self):
        self.headers: List = []
        self.header_style_row: Optional[tuple] = None
        self.header_cells: int = 0
        self.groups: Dict[str, list] = {}
        self.leading: List[tuple] = []
        self.tail: List[tuple] = []
        self.styles = StyleTable()
        self.layout: Optional[SheetLayout] = None
        self.row_count: int = 0
        self.column_index: Optional[int] = None

    def header_style_dicts(self) -> List[Optional[dict]]:
        return self.styles.row_dicts(self.header_style_row)


def read_grouped_data(
    file_path: str,
    sheet_name: str,
    column: str,
    header_row: int = 1,
    data_only: bool = True,
    include_lead_rows: bool = True,
    tail_rows_start: int = 0,
    tail_rows_end: int = 0,
) -> ReadResult:
    """一次遍历读取工作表：按列分组，同时保留样式与版式。

    * ``headers`` / ``header_style_row``：表头行（1-indexed 的 header_row）
    * ``groups``：``{value: [(src_row, values, style_row), ...]}``
    * ``leading``：第 1 行到 header_row-1 行
    * ``tail``：tail_rows_start..tail_rows_end 行
    * ``styles`` / ``layout``：样式表与版式快照
    """
    result = ReadResult()
    wb = openpyxl.load_workbook(file_path, data_only=data_only)
    try:
        ws = wb[sheet_name]
        table = result.styles
        result.layout = SheetLayout.capture(ws)

        want_tail = tail_rows_start > 0 and tail_rows_end >= tail_rows_start
        tail_range = range(tail_rows_start, tail_rows_end + 1) if want_tail else range(0)
        want_lead = include_lead_rows and header_row > 1

        header_seen = False
        headers_str: List[str] = []
        column_index: Optional[int] = None
        found = False
        max_row = 0

        for src_row, row_cells in enumerate(ws.iter_rows(), start=1):
            max_row = src_row
            if not header_seen:
                if src_row == header_row:
                    header_seen = True
                    result.headers = [c.value for c in row_cells]
                    result.header_style_row = table.intern_row(row_cells)
                    result.header_cells = len(row_cells)
                    headers_str = [
                        str(h) if h is not None else f"Col{i}"
                        for i, h in enumerate(result.headers)
                    ]
                    if column in headers_str:
                        column_index = headers_str.index(column)
                        found = True
                elif want_lead:
                    result.leading.append(
                        (src_row, [c.value for c in row_cells], table.intern_row(row_cells))
                    )
                continue

            if not found:
                continue
            if want_tail and src_row in tail_range:
                result.tail.append(
                    (src_row, [c.value for c in row_cells], table.intern_row(row_cells))
                )
                continue

            col_idx = column_index
            key = row_cells[col_idx].value if col_idx < len(row_cells) else None
            key = "(空)" if key is None else str(key)
            result.groups.setdefault(key, []).append(
                (src_row, [c.value for c in row_cells], table.intern_row(row_cells))
            )

        result.column_index = column_index
        result.row_count = max_row
        # 与旧实现保持一致：目标范围超出工作表时视为空
        if want_lead and max_row < header_row - 1:
            result.leading = []
        if want_tail and max_row < tail_rows_end:
            result.tail = []
        return result
    finally:
        wb.close()


# ── 兼容包装：旧返回结构 ────────────────────────────────────────────

def read_sheet_grouped_with_styles(
    file_path: str,
    sheet_name: str,
    column: str,
    header_row: int = 1,
    data_only: bool = True,
) -> tuple:
    """以普通模式读取工作表，按列分组，同时保留单元格样式。

    返回 (headers, header_styles, groups)，groups 为
    ``{value: [(src_row, row_values, row_styles), ...]}``，样式是字典列表。

    新代码应优先使用 ``read_grouped_data``：返回的样式是共享的整数 id，
    大表内存占用低得多。
    """
    result = read_grouped_data(file_path, sheet_name, column,
                               header_row=header_row, data_only=data_only,
                               include_lead_rows=False)
    table = result.styles
    groups = {
        key: [(row, values, table.row_dicts(style_row)) for row, values, style_row in rows]
        for key, rows in result.groups.items()
    }
    return result.headers, result.header_style_dicts(), groups


def get_sheet_names(file_path: str) -> List[str]:
    wb = openpyxl.load_workbook(file_path, read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


def get_columns(file_path: str, sheet_name: str, header_row: int = 1) -> List[str]:
    """读取指定行作为列名（1-indexed，默认为第 1 行）。"""
    wb = openpyxl.load_workbook(file_path, read_only=True)
    try:
        ws = wb[sheet_name]
        row = next(ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True))
        return [str(c) if c is not None else f"Col{i}" for i, c in enumerate(row)]
    finally:
        wb.close()


def get_unique_values(file_path: str, sheet_name: str, column: str, header_row: int = 1) -> Dict[str, int]:
    """获取指定列的所有唯一值及其计数（1-indexed header_row）。"""
    wb = openpyxl.load_workbook(file_path, read_only=True)
    try:
        ws = wb[sheet_name]
        header_iter = ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True)
        try:
            headers = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(next(header_iter))]
        except StopIteration:
            return {}
        if column not in headers:
            return {}
        col_idx = headers.index(column)
        counts: Dict[str, int] = {}
        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            if col_idx < len(row):
                val = row[col_idx]
                val = "(空)" if val is None else str(val)
            else:
                val = "(空)"
            counts[val] = counts.get(val, 0) + 1
        return counts
    finally:
        wb.close()


def read_sheet_grouped(
    file_path: str,
    sheet_name: str,
    column: str,
    header_row: int = 1,
) -> tuple:
    """流式读取并按列分组。返回 (headers, {value: [row_tuple, ...]})。"""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        row_iter = ws.iter_rows(values_only=True)

        for _ in range(header_row - 1):
            try:
                next(row_iter)
            except StopIteration:
                return [], {}

        try:
            header_row_data = next(row_iter)
        except StopIteration:
            return [], {}

        headers = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(header_row_data)]
        if column not in headers:
            return headers, {}
        col_idx = headers.index(column)

        groups: Dict[str, list] = {}
        for row in row_iter:
            key = row[col_idx] if col_idx < len(row) else None
            key = "(空)" if key is None else str(key)
            groups.setdefault(key, []).append(tuple(row))
        return headers, groups
    finally:
        wb.close()


# ── 前置行读取 ──────────────────────────────────────────────────────

def read_leading_rows_with_styles(
    file_path: str,
    sheet_name: str,
    start_row: int,
    end_row: int,
    data_only: bool = True,
) -> list:
    """读取源文件中指定行范围的行及其样式（有界读取，只取需要的行）。"""
    if start_row < 1 or end_row < start_row:
        return []
    wb = openpyxl.load_workbook(file_path, data_only=data_only)
    try:
        ws = wb[sheet_name]
        leading = []
        for i, row_cells in enumerate(
            ws.iter_rows(min_row=start_row, max_row=end_row), start=start_row
        ):
            leading.append((i, [c.value for c in row_cells], _extract_row_styles(row_cells)))
        return leading if len(leading) == end_row - start_row + 1 else []
    finally:
        wb.close()


# ── 合并单元格复制 ──────────────────────────────────────────────────

def copy_merged_cells(
    src_ws,
    dst_ws,
    row_range_start: int,
    row_range_end: int,
    row_shift: int = 0,
):
    """将源工作表中指定行范围内的合并单元格复制到目标工作表。"""
    for merged_range in src_ws.merged_cells.ranges:
        if merged_range.min_row < row_range_start or merged_range.max_row > row_range_end:
            continue
        new_min_row = merged_range.min_row + row_shift
        new_max_row = merged_range.max_row + row_shift
        try:
            start_cell = f"{_get_column_letter(merged_range.min_col)}{new_min_row}"
            end_cell = f"{_get_column_letter(merged_range.max_col)}{new_max_row}"
            dst_ws.merge_cells(f"{start_cell}:{end_cell}")
        except Exception:
            pass  # 合并区域冲突时静默跳过


def copy_merged_cells_with_map(
    src_ws,
    dst_ws,
    row_map: Dict[int, int],
):
    """根据行号映射将合并单元格复制到目标工作表。"""
    if not row_map:
        return
    for merged_range in src_ws.merged_cells.ranges:
        src_min_row = merged_range.min_row
        src_max_row = merged_range.max_row
        if src_min_row not in row_map or src_max_row not in row_map:
            continue
        new_min_row = row_map[src_min_row]
        new_max_row = row_map[src_max_row]
        try:
            start_cell = f"{_get_column_letter(merged_range.min_col)}{new_min_row}"
            end_cell = f"{_get_column_letter(merged_range.max_col)}{new_max_row}"
            dst_ws.merge_cells(f"{start_cell}:{end_cell}")
        except Exception:
            pass


# ── 行范围预览 ──────────────────────────────────────────────────────

def read_row_range_preview(
    file_path: str,
    sheet_name: str,
    start_row: int,
    end_row: int,
    max_cells: int = 3,
) -> str:
    """读取指定行范围的前几列内容，用于 UI 预览。

    只读取 ``start_row..end_row``；范围超出工作表时返回空串（与旧行为一致）。
    """
    if start_row < 1 or end_row < start_row:
        return ""
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            ws = wb[sheet_name]
            max_row = ws.max_row
            if max_row is not None and max_row < end_row:
                return ""
            parts = []
            for i, row_data in enumerate(
                ws.iter_rows(min_row=start_row, max_row=end_row, values_only=True),
                start=start_row,
            ):
                cells = [str(c) for c in row_data[:max_cells] if c is not None]
                row_label = f"Row{i}"
                parts.append(f"{row_label}: {', '.join(cells)}" if cells else row_label)
            if len(parts) < end_row - start_row + 1:
                return ""
            return "; ".join(parts) if parts else ""
        finally:
            wb.close()
    except Exception:
        return ""
