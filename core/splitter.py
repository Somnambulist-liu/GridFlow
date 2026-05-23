import os
from typing import Dict
import openpyxl
from PySide6.QtCore import QThread, Signal

from core.reader import read_sheet_grouped


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

    # ── values-only mode (fast, current default) ──────────────────

    def _run_values_only(self):
        self.progress.emit(0, 1, "正在读取数据...")
        headers, groups = read_sheet_grouped(self.file_path, self.sheet_name, self.column)

        if not groups:
            self.finished.emit("没有数据需要拆分")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        total = len(groups)

        if self.mode == "files":
            summary_parts = self._split_to_files(headers, groups, total)
        else:
            summary_parts = self._split_to_sheets(headers, groups, total)

        unit = "文件" if self.mode == "files" else "Sheet"
        total_rows = sum(p[1] for p in summary_parts)
        summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行"
        self.progress.emit(total, total, summary)
        self.finished.emit(summary)

    def _split_to_files(self, headers: list, groups: Dict[str, list], total: int):
        summary = []
        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_filename(str(value))
            filename = self.name_pattern.replace("{value}", safe_name)
            filepath = os.path.join(self.output_dir, filename)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = safe_name[:31]
            if self.keep_header:
                ws.append(headers)
            for row in rows:
                ws.append(row)
            wb.save(filepath)
            wb.close()

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成：{safe_name} ({len(rows)} 行)")
        return summary

    def _split_to_sheets(self, headers: list, groups: Dict[str, list], total: int):
        summary = []
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_sheet_name(str(value))
            ws = wb.create_sheet(title=safe_name)
            if self.keep_header:
                ws.append(headers)
            for row in rows:
                ws.append(row)

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成 Sheet：{safe_name} ({len(rows)} 行)")

        wb.save(self.output_path)
        wb.close()
        return summary

    # ── formula-preserving mode (slower, preserves =SUM etc.) ─────

    def _run_with_formulas(self):
        """Split while preserving cell formulas.

        Opens source in normal mode, extracts cell values immediately
        (including formula strings) before closing the source workbook.
        """
        self.progress.emit(0, 1, "正在读取数据（保留公式）...")
        wb = openpyxl.load_workbook(self.file_path)
        ws = wb[self.sheet_name]

        # Read all rows at once, extracting values immediately
        all_rows = list(ws.iter_rows())

        if not all_rows:
            wb.close()
            self.finished.emit("表格为空")
            return

        header_cells = all_rows[0]
        headers = [c.value for c in header_cells]
        headers_str = [str(h) if h is not None else f"Col{i}" for i, h in enumerate(headers)]

        if self.column not in headers_str:
            wb.close()
            self.finished.emit(f"未找到字段：{self.column}")
            return

        col_idx = headers_str.index(self.column)

        # Extract values immediately — do NOT store Cell objects past wb.close()
        groups: Dict[str, list] = {}
        for row_cells in all_rows[1:]:
            key = row_cells[col_idx].value if col_idx < len(row_cells) else None
            key = "(空)" if key is None else str(key)
            row_values = [c.value for c in row_cells]
            groups.setdefault(key, []).append(row_values)

        header_values = [c.value for c in header_cells]
        wb.close()

        if not groups:
            self.finished.emit("没有数据需要拆分")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        total = len(groups)

        if self.mode == "files":
            summary_parts = self._split_files_formulas(header_values, groups, total)
        else:
            summary_parts = self._split_sheets_formulas(header_values, groups, total)

        unit = "文件" if self.mode == "files" else "Sheet"
        total_rows = sum(p[1] for p in summary_parts)
        summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行（含公式）"
        self.progress.emit(total, total, summary)
        self.finished.emit(summary)

    def _split_files_formulas(self, headers, groups, total):
        summary = []
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
            if self.keep_header:
                self._write_row(out_ws, 1, headers)
                start_row = 2

            for r_idx, row_values in enumerate(rows, start_row):
                self._write_row(out_ws, r_idx, row_values)

            out_wb.save(filepath)
            out_wb.close()

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成：{safe_name} ({len(rows)} 行)")
        return summary

    def _split_sheets_formulas(self, headers, groups, total):
        summary = []
        out_wb = openpyxl.Workbook()
        out_wb.remove(out_wb.active)

        for i, (value, rows) in enumerate(groups.items()):
            if self._is_cancelled:
                break
            safe_name = _safe_sheet_name(str(value))
            out_ws = out_wb.create_sheet(title=safe_name)

            start_row = 1
            if self.keep_header:
                self._write_row(out_ws, 1, headers)
                start_row = 2

            for r_idx, row_values in enumerate(rows, start_row):
                self._write_row(out_ws, r_idx, row_values)

            summary.append((value, len(rows)))
            self.progress.emit(i + 1, total, f"正在生成 Sheet：{safe_name} ({len(rows)} 行)")

        out_wb.save(self.output_path)
        out_wb.close()
        return summary

    @staticmethod
    def _write_row(ws, row_idx, values):
        """Write a row of values, preserving formulas (strings starting with =)."""
        for col_idx, val in enumerate(values, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)


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
