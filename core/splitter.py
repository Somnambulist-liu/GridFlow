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
    ):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.column = column
        self.mode = mode
        self.output_dir = output_dir
        self.output_path = output_path
        self.name_pattern = name_pattern
        self.keep_header = keep_header

    def run(self):
        try:
            self.progress.emit(0, 1, "正在读取数据...")
            headers, groups = read_sheet_grouped(self.file_path, self.sheet_name, self.column)

            if not groups:
                self.finished.emit("没有数据需要拆分")
                return

            os.makedirs(self.output_dir, exist_ok=True)
            total = len(groups)
            summary_parts = []

            if self.mode == "files":
                summary_parts = self._split_to_files(headers, groups, total)
            else:
                summary_parts = self._split_to_sheets(headers, groups, total)

            unit = "文件" if self.mode == "files" else "Sheet"
            total_rows = sum(p[1] for p in summary_parts)
            summary = f"拆分完成！共生成 {len(summary_parts)} 个{unit}，总计 {total_rows} 行"
            self.progress.emit(total, total, summary)
            self.finished.emit(summary)

        except Exception as e:
            self.error_occurred.emit(str(e))

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
