import os
from typing import Dict
import openpyxl
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter
from PySide6.QtCore import QThread, Signal

from core.reader import (
    read_grouped_data,
    StyleApplier,
)


class SplitWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def configure(
        self,
        file_path: str,
        sheet_name: str,
        column: str,
        mode: str,
        output_dir: str,
        output_path: str,
        name_pattern: str = "{value}.xlsx",
        keep_header: bool = True,
        preserve_formulas: bool = False,
        header_row: int = 1,
        include_lead_rows: bool = True,
        include_tail_rows: bool = False,
        tail_rows_start: int = 0,
        tail_rows_end: int = 0,
    ):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.column = column
        self.mode = mode
        self.output_dir = output_dir
        self.output_path = output_path
        self.name_pattern = name_pattern
        self.keep_header = keep_header
        self.preserve_formulas = preserve_formulas
        self.header_row = header_row
        self.include_lead_rows = include_lead_rows
        self.include_tail_rows = include_tail_rows
        self.tail_rows_start = tail_rows_start
        self.tail_rows_end = tail_rows_end

    def run(self):
        try:
            if self.preserve_formulas:
                self._run_with_formulas()
            else:
                self._run_values_only()
        except Exception as e:
            self.error_occurred.emit(str(e))

    # ── 读取 ──────────────────────────────────────────────────────

    def _read(self, data_only: bool):
        """一次遍历读取：值 + 样式 + 版式（列宽/行高/合并区域）。"""
        return read_grouped_data(
            self.file_path, self.sheet_name, self.column,
            header_row=self.header_row,
            data_only=data_only,
            include_lead_rows=self.include_lead_rows,
            tail_rows_start=self.tail_rows_start if self.include_tail_rows else 0,
            tail_rows_end=self.tail_rows_end if self.include_tail_rows else 0,
        )

    def _exclude_tail_from_groups(self, groups: dict) -> dict:
        """从分组数据中移除尾部行（避免尾部行被当作数据拆分）。"""
        if not self.include_tail_rows or self.tail_rows_start <= 0:
            return groups
        tail_src_rows = set(range(self.tail_rows_start, self.tail_rows_end + 1))
        cleaned = {}
        for key, rows in groups.items():
            filtered = [(r, v, s) for r, v, s in rows if r not in tail_src_rows]
            if filtered:
                cleaned[key] = filtered
        return cleaned

    # ── values-only mode (preserves cell styles) ──────────────────

    def _run_values_only(self):
        self.progress.emit(0, 1, "正在读取数据...")
        data = self._read(data_only=True)

        if not data.groups:
            self.finished.emit("没有数据需要拆分")
            return

        # 从分组中排除尾部行
        groups = self._exclude_tail_from_groups(data.groups)
        if not groups:
            self.finished.emit("没有数据需要拆分")
            return

        leading_rows = data.leading
        tail_rows = data.tail

        os.makedirs(self.output_dir, exist_ok=True)
        total = len(groups)

        if self.mode == "files":
            summary_parts = self._split_to_files(data, groups, total,
                                                 leading_rows=leading_rows, tail_rows=tail_rows)
        else:
            summary_parts = self._split_to_sheets(data, groups, total,
                                                  leading_rows=leading_rows, tail_rows=tail_rows)

        unit = "文件" if self.mode == "files" else "Sheet"
        total_rows = sum(p[1] for p in summary_parts)
        summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行"
        self.progress.emit(total, total, summary)
        self.finished.emit(summary)

    def _fill_sheet(self, ws, data, rows, leading_rows, tail_rows, applier):
        """把前置行 + 表头 + 数据行 + 尾部行写入目标工作表，返回行号映射。"""
        row_map = {}
        cur = 1

        table = data.styles

        # 1. 前置行
        for l_idx, (src_row, row_values, style_row) in enumerate(leading_rows, cur):
            self._write_row(ws, l_idx, row_values, style_row=style_row,
                            applier=applier, table=table)
            row_map[src_row] = l_idx
            cur = l_idx + 1

        # 2. 表头行
        if self.keep_header:
            self._write_row(ws, cur, data.headers, style_row=data.header_style_row,
                            applier=applier, table=table)
            row_map[self.header_row] = cur
            cur += 1

        # 3. 数据行
        for r_idx, (src_row, row_values, style_row) in enumerate(rows, cur):
            self._write_row(ws, r_idx, row_values, style_row=style_row,
                            applier=applier, table=table)
            row_map[src_row] = r_idx
            cur = r_idx + 1

        # 4. 尾部行
        for t_idx, (src_row, row_values, style_row) in enumerate(tail_rows, cur):
            self._write_row(ws, t_idx, row_values, style_row=style_row,
                            applier=applier, table=table)
            row_map[src_row] = t_idx
            cur = t_idx + 1

        return row_map

    def _split_to_files(self, data, groups, total, col_letters=None,
                        leading_rows=None, tail_rows=None):
        """按分组值拆分为多个 .xlsx 文件，保留单元格样式和列宽/行高。"""
        _leading = leading_rows or []
        _tail = tail_rows or []
        summary = []
        layout = data.layout

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_filename(str(value))
            filename = self.name_pattern.replace("{value}", safe_name)
            filepath = os.path.join(self.output_dir, filename)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = safe_name[:31]

            applier = StyleApplier(wb)
            row_map = self._fill_sheet(ws, data, rows, _leading, _tail, applier)
            applier.close()

            # 5. 复制列宽和行高
            layout.apply_column_widths(ws)
            layout.apply_row_heights(ws, row_map)

            # 6. 复制合并单元格
            layout.apply_merged(ws, row_map)

            wb.save(filepath)
            wb.close()

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成：{safe_name} ({len(rows)} 行)")

        return summary

    def _split_to_sheets(self, data, groups, total, col_letters=None,
                         leading_rows=None, tail_rows=None):
        """按分组值拆分为单个 .xlsx 中的多个 Sheet。"""
        _leading = leading_rows or []
        _tail = tail_rows or []
        summary = []
        layout = data.layout

        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        applier = StyleApplier(wb)

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_sheet_name(str(value))
            ws = wb.create_sheet(title=safe_name)

            row_map = self._fill_sheet(ws, data, rows, _leading, _tail, applier)

            # 5. 复制列宽和行高
            layout.apply_column_widths(ws)
            layout.apply_row_heights(ws, row_map)

            # 6. 复制合并单元格
            layout.apply_merged(ws, row_map)

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成 Sheet：{safe_name} ({len(rows)} 行)")

        applier.close()
        wb.save(self.output_path)
        wb.close()
        return summary

    # ── formula-preserving mode (preserves formulas AND cell styles) ──

    def _run_with_formulas(self):
        """Split while preserving cell formulas AND cell styles."""
        self.progress.emit(0, 1, "正在读取数据（保留公式和样式）...")
        data = self._read(data_only=False)

        if not data.headers:
            self.finished.emit("表格为空")
            return

        headers_str = [str(h) if h is not None else f"Col{i}"
                       for i, h in enumerate(data.headers)]
        if self.column not in headers_str:
            self.finished.emit(f"未找到字段：{self.column}")
            return

        # Pre-compute column letters for formula coordinate translation
        col_letters = [get_column_letter(i) for i in range(1, data.header_cells + 1)]

        # 从分组中排除尾部行
        groups = self._exclude_tail_from_groups(data.groups)
        if not groups:
            self.finished.emit("没有数据需要拆分")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        total = len(groups)

        if self.mode == "files":
            summary_parts = self._split_files_formulas(
                data, col_letters, groups, total,
                leading_rows=data.leading, tail_rows=data.tail)
        else:
            summary_parts = self._split_sheets_formulas(
                data, col_letters, groups, total,
                leading_rows=data.leading, tail_rows=data.tail)

        unit = "文件" if self.mode == "files" else "Sheet"
        total_rows = sum(p[1] for p in summary_parts)
        summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行（含公式）"
        self.progress.emit(total, total, summary)
        self.finished.emit(summary)

    def _fill_sheet_formulas(self, ws, data, col_letters, rows, leading_rows, tail_rows, applier):
        """公式模式：写法与 _fill_sheet 相同，但数据行会翻译公式引用。"""
        row_map = {}
        cur = 1
        table = data.styles

        # 1. 前置行
        for l_idx, (src_row, row_values, style_row) in enumerate(leading_rows, cur):
            self._write_row(ws, l_idx, row_values, col_letters, src_row,
                            style_row=style_row, applier=applier, table=table)
            row_map[src_row] = l_idx
            cur = l_idx + 1

        # 2. 表头行
        if self.keep_header:
            self._write_row(ws, cur, data.headers, col_letters,
                            style_row=data.header_style_row, applier=applier, table=table)
            row_map[self.header_row] = cur
            cur += 1

        # 3. 数据行
        for r_idx, (src_row, row_values, style_row) in enumerate(rows, cur):
            self._write_row(ws, r_idx, row_values, col_letters, src_row,
                            style_row=style_row, applier=applier, table=table)
            row_map[src_row] = r_idx
            cur = r_idx + 1

        # 4. 尾部行（公式模式同样翻译引用，与旧实现一致）
        for t_idx, (src_row, row_values, style_row) in enumerate(tail_rows, cur):
            self._write_row(ws, t_idx, row_values, col_letters, src_row,
                            style_row=style_row, applier=applier, table=table)
            row_map[src_row] = t_idx
            cur = t_idx + 1

        return row_map

    def _split_files_formulas(self, data, col_letters, groups, total,
                              leading_rows=None, tail_rows=None):
        """按分组值拆分为多个文件，保留公式和单元格样式。"""
        _leading = leading_rows or []
        _tail = tail_rows or []
        summary = []
        layout = data.layout

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_filename(str(value))
            filename = self.name_pattern.replace("{value}", safe_name)
            filepath = os.path.join(self.output_dir, filename)

            out_wb = openpyxl.Workbook()
            out_ws = out_wb.active
            out_ws.title = safe_name[:31]

            applier = StyleApplier(out_wb)
            row_map = self._fill_sheet_formulas(out_ws, data, col_letters, rows,
                                                _leading, _tail, applier)
            applier.close()

            # 5. 复制列宽和行高
            layout.apply_column_widths(out_ws)
            layout.apply_row_heights(out_ws, row_map)

            # 6. 复制合并单元格
            layout.apply_merged(out_ws, row_map)

            out_wb.save(filepath)
            out_wb.close()

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成：{safe_name} ({len(rows)} 行)")

        return summary

    def _split_sheets_formulas(self, data, col_letters, groups, total,
                               leading_rows=None, tail_rows=None):
        """按分组值拆分为单个文件中的多个 Sheet，保留公式和单元格样式。"""
        _leading = leading_rows or []
        _tail = tail_rows or []
        summary = []
        layout = data.layout

        out_wb = openpyxl.Workbook()
        out_wb.remove(out_wb.active)
        applier = StyleApplier(out_wb)

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_sheet_name(str(value))
            out_ws = out_wb.create_sheet(title=safe_name)

            row_map = self._fill_sheet_formulas(out_ws, data, col_letters, rows,
                                                _leading, _tail, applier)

            # 5. 复制列宽和行高
            layout.apply_column_widths(out_ws)
            layout.apply_row_heights(out_ws, row_map)

            # 6. 复制合并单元格
            layout.apply_merged(out_ws, row_map)

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成 Sheet：{safe_name} ({len(rows)} 行)")

        applier.close()
        out_wb.save(self.output_path)
        out_wb.close()
        return summary

    @staticmethod
    def _write_row(ws, row_idx, values, col_letters=None, src_row=None,
                   style_row=None, applier=None, table=None):
        """Write a row of values, translating formula references and applying cell styles.

        Args:
            ws: target worksheet
            row_idx: 1-based row index in the target sheet
            values: list of cell values
            col_letters: column letters for formula translation
            src_row: source row number for formula translation
            style_row: tuple of interned style ids (from StyleTable)
            applier: StyleApplier resolving source ids to target styles
            table: StyleTable owning the style ids
        """
        translate = bool(col_letters) and bool(src_row)
        has_style = style_row is not None and applier is not None
        for col_idx, val in enumerate(values, 1):
            if translate and isinstance(val, str) and val.startswith("="):
                src_cell = f"{col_letters[col_idx - 1]}{src_row}"
                tgt_cell = f"{get_column_letter(col_idx)}{row_idx}"
                try:
                    val = Translator(val, origin=src_cell).translate_formula(tgt_cell)
                except Exception:
                    pass  # formula references out of range — keep original
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            if has_style and col_idx - 1 < len(style_row):
                style_id = style_row[col_idx - 1]
                if style_id:
                    applier.apply(cell, style_id, table)


def _safe_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip()[:100]


def _safe_sheet_name(name: str) -> str:
    invalid = '[]:*?/\\'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip()[:31]
