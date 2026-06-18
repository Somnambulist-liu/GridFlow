import os
from typing import Dict
import openpyxl
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter
from PySide6.QtCore import QThread, Signal

from core.reader import (
    read_sheet_grouped_with_styles,
    _apply_style_to_cell,
    _extract_row_styles,
    _copy_column_widths,
    _copy_row_heights,
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

    def run(self):
        try:
            if self.preserve_formulas:
                self._run_with_formulas()
            else:
                self._run_values_only()
        except Exception as e:
            self.error_occurred.emit(str(e))

    # ── values-only mode (preserves cell styles) ──────────────────

    def _run_values_only(self):
        self.progress.emit(0, 1, "正在读取数据...")
        headers, header_styles, groups = read_sheet_grouped_with_styles(
            self.file_path, self.sheet_name, self.column, data_only=True
        )

        if not groups:
            self.finished.emit("没有数据需要拆分")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        total = len(groups)

        if self.mode == "files":
            summary_parts = self._split_to_files(headers, header_styles, groups, total)
        else:
            summary_parts = self._split_to_sheets(headers, header_styles, groups, total)

        unit = "文件" if self.mode == "files" else "Sheet"
        total_rows = sum(p[1] for p in summary_parts)
        summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行"
        self.progress.emit(total, total, summary)
        self.finished.emit(summary)

    def _split_to_files(self, headers, header_styles, groups, total, col_letters=None):
        """按分组值拆分为多个 .xlsx 文件，保留单元格样式和列宽/行高。

        groups 格式: {value: [(src_row, row_values, row_styles), ...]}
        """
        summary = []
        # 打开源工作簿以复制列宽和行高
        src_wb = openpyxl.load_workbook(self.file_path)
        src_ws = src_wb[self.sheet_name]

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_filename(str(value))
            filename = self.name_pattern.replace("{value}", safe_name)
            filepath = os.path.join(self.output_dir, filename)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = safe_name[:31]

            start_row = 1
            if self.keep_header:
                self._write_row(ws, 1, headers, col_letters, styles=header_styles)
                start_row = 2

            row_map = {}
            for r_idx, (src_row, row_values, row_styles) in enumerate(rows, start_row):
                self._write_row(ws, r_idx, row_values, col_letters, styles=row_styles)
                row_map[src_row] = r_idx

            # 复制列宽和行高
            _copy_column_widths(src_ws, ws)
            if self.keep_header:
                row_map[1] = 1  # 表头行
            _copy_row_heights(src_ws, ws, row_map)

            wb.save(filepath)
            wb.close()

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成：{safe_name} ({len(rows)} 行)")

        src_wb.close()
        return summary

    def _split_to_sheets(self, headers, header_styles, groups, total, col_letters=None):
        """按分组值拆分为单个 .xlsx 中的多个 Sheet，保留单元格样式和列宽/行高。

        groups 格式: {value: [(src_row, row_values, row_styles), ...]}
        """
        summary = []
        # 打开源工作簿以复制列宽和行高
        src_wb = openpyxl.load_workbook(self.file_path)
        src_ws = src_wb[self.sheet_name]

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_sheet_name(str(value))
            ws = wb.create_sheet(title=safe_name)

            start_row = 1
            if self.keep_header:
                self._write_row(ws, 1, headers, col_letters, styles=header_styles)
                start_row = 2

            row_map = {}
            for r_idx, (src_row, row_values, row_styles) in enumerate(rows, start_row):
                self._write_row(ws, r_idx, row_values, col_letters, styles=row_styles)
                row_map[src_row] = r_idx

            # 复制列宽和行高
            _copy_column_widths(src_ws, ws)
            if self.keep_header:
                row_map[1] = 1  # 表头行
            _copy_row_heights(src_ws, ws, row_map)

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成 Sheet：{safe_name} ({len(rows)} 行)")

        wb.save(self.output_path)
        wb.close()
        src_wb.close()
        return summary

    # ── formula-preserving mode (preserves formulas AND cell styles) ──

    def _run_with_formulas(self):
        """Split while preserving cell formulas AND cell styles.

        Opens source in normal mode, extracts cell values (including formula
        strings) and styles before closing the source workbook.
        """
        self.progress.emit(0, 1, "正在读取数据（保留公式和样式）...")
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb[self.sheet_name]

        # Read all rows at once, extracting values and styles immediately
        all_rows = list(ws.iter_rows())

        if not all_rows:
            wb.close()
            self.finished.emit("表格为空")
            return

        header_cells = all_rows[0]
        headers = [c.value for c in header_cells]
        header_styles = _extract_row_styles(header_cells)
        headers_str = [str(h) if h is not None else f"Col{i}" for i, h in enumerate(headers)]

        if self.column not in headers_str:
            wb.close()
            self.finished.emit(f"未找到字段：{self.column}")
            return

        col_idx = headers_str.index(self.column)

        # Pre-compute column letters for formula coordinate translation
        col_letters = [get_column_letter(i) for i in range(1, len(header_cells) + 1)]

        # Extract values and styles immediately — do NOT store Cell objects past wb.close()
        # Store (src_row, row_values, row_styles) so formulas can be translated
        groups: Dict[str, list] = {}
        for src_row, row_cells in enumerate(all_rows[1:], start=2):
            key = row_cells[col_idx].value if col_idx < len(row_cells) else None
            key = "(空)" if key is None else str(key)
            row_values = [c.value for c in row_cells]
            row_styles = _extract_row_styles(row_cells)
            groups.setdefault(key, []).append((src_row, row_values, row_styles))

        wb.close()

        if not groups:
            self.finished.emit("没有数据需要拆分")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        total = len(groups)

        if self.mode == "files":
            summary_parts = self._split_files_formulas(headers, header_styles, col_letters, groups, total)
        else:
            summary_parts = self._split_sheets_formulas(headers, header_styles, col_letters, groups, total)

        unit = "文件" if self.mode == "files" else "Sheet"
        total_rows = sum(p[1] for p in summary_parts)
        summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行（含公式）"
        self.progress.emit(total, total, summary)
        self.finished.emit(summary)

    def _split_files_formulas(self, headers, header_styles, col_letters, groups, total):
        """按分组值拆分为多个文件，保留公式和单元格样式。"""
        summary = []
        # 打开源工作簿以复制列宽和行高
        src_wb = openpyxl.load_workbook(self.file_path)
        src_ws = src_wb[self.sheet_name]

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_filename(str(value))
            filename = self.name_pattern.replace("{value}", safe_name)
            filepath = os.path.join(self.output_dir, filename)

            out_wb = openpyxl.Workbook()
            out_ws = out_wb.active
            out_ws.title = safe_name[:31]

            start_row = 1
            row_map = {}
            if self.keep_header:
                self._write_row(out_ws, 1, headers, col_letters, styles=header_styles)
                row_map[1] = 1
                start_row = 2

            for r_idx, (src_row, row_values, row_styles) in enumerate(rows, start_row):
                self._write_row(out_ws, r_idx, row_values, col_letters, src_row, styles=row_styles)
                row_map[src_row] = r_idx

            # 复制列宽和行高
            _copy_column_widths(src_ws, out_ws)
            _copy_row_heights(src_ws, out_ws, row_map)

            out_wb.save(filepath)
            out_wb.close()

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成：{safe_name} ({len(rows)} 行)")

        src_wb.close()
        return summary

    def _split_sheets_formulas(self, headers, header_styles, col_letters, groups, total):
        """按分组值拆分为单个文件中的多个 Sheet，保留公式和单元格样式。"""
        summary = []
        # 打开源工作簿以复制列宽和行高
        src_wb = openpyxl.load_workbook(self.file_path)
        src_ws = src_wb[self.sheet_name]

        out_wb = openpyxl.Workbook()
        out_wb.remove(out_wb.active)

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_sheet_name(str(value))
            out_ws = out_wb.create_sheet(title=safe_name)

            start_row = 1
            row_map = {}
            if self.keep_header:
                self._write_row(out_ws, 1, headers, col_letters, styles=header_styles)
                row_map[1] = 1
                start_row = 2

            for r_idx, (src_row, row_values, row_styles) in enumerate(rows, start_row):
                self._write_row(out_ws, r_idx, row_values, col_letters, src_row, styles=row_styles)
                row_map[src_row] = r_idx

            # 复制列宽和行高
            _copy_column_widths(src_ws, out_ws)
            _copy_row_heights(src_ws, out_ws, row_map)

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成 Sheet：{safe_name} ({len(rows)} 行)")

        out_wb.save(self.output_path)
        out_wb.close()
        src_wb.close()
        return summary

    @staticmethod
    def _write_row(ws, row_idx, values, col_letters=None, src_row=None, styles=None):
        """Write a row of values, translating formula references and applying cell styles.

        Args:
            ws: target worksheet
            row_idx: 1-based row index in the target sheet
            values: list of cell values
            col_letters: column letters for formula translation
            src_row: source row number for formula translation
            styles: list of style dicts (from _extract_cell_style), or None
        """
        for col_idx, val in enumerate(values, 1):
            if col_letters and src_row and isinstance(val, str) and val.startswith("="):
                src_cell = f"{col_letters[col_idx - 1]}{src_row}"
                tgt_cell = f"{get_column_letter(col_idx)}{row_idx}"
                try:
                    val = Translator(val, origin=src_cell).translate_formula(tgt_cell)
                except Exception:
                    pass  # formula references out of range — keep original
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            if styles and col_idx - 1 < len(styles):
                _apply_style_to_cell(cell, styles[col_idx - 1])


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
