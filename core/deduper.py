import os
import openpyxl
from PySide6.QtCore import QThread, Signal

from core.reader import StreamedWorkbook


class DedupWorker(QThread):
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
        columns: list,
        keep: str = "first",
        output_dir: str = "",
    ):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.columns = columns
        self.keep = keep
        self.output_dir = output_dir

    def run(self):
        try:
            if self.keep == "last":
                self._run_keep_last()
            else:
                self._run_keep_first()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _open_source(self):
        """返回 (workbook, row_iterator, headers)；表头读不到时抛 StopIteration。"""
        wb = openpyxl.load_workbook(self.file_path, read_only=True)
        ws = wb[self.sheet_name]
        it = ws.iter_rows(values_only=True)
        headers = [str(c) if c is not None else f"Col{j}"
                   for j, c in enumerate(next(it))]
        col_indices = [headers.index(c) for c in self.columns if c in headers]
        return wb, it, headers, col_indices

    def _run_keep_first(self):
        """保留首次出现的行：边扫边写，内存只与唯一值数量相关。"""
        self.progress.emit(0, 3, "正在读取数据...")
        wb = None
        try:
            try:
                wb, it, headers, col_indices = self._open_source()
            except StopIteration:
                self.finished.emit("没有数据")
                return

            if not col_indices:
                self.finished.emit("未找到指定的去重列")
                return

            with StreamedWorkbook() as out:
                out_ws = out.sheet()
                out_ws.append(headers)

                seen = set()
                dup_count = 0
                kept = 0
                for row in it:
                    key = self._key(row, col_indices)
                    if key in seen:
                        dup_count += 1
                        continue
                    seen.add(key)
                    out_ws.append(row)
                    kept += 1

                if dup_count == 0:
                    # 没有重复就不产出文件，__exit__ 顺手清掉临时文件
                    self.finished.emit("没有发现重复数据")
                    return

                self.progress.emit(1, 3, f"发现 {dup_count} 行重复，正在生成去重文件...")
                base = os.path.splitext(os.path.basename(self.file_path))[0]
                out.save(os.path.join(self.output_dir, f"{base}_去重结果.xlsx"))
        finally:
            if wb is not None:
                wb.close()

        summary = f"去重完成！删除了 {dup_count} 行重复数据，保留 {kept} 行"
        self.progress.emit(3, 3, summary)
        self.finished.emit(summary)

    def _run_keep_last(self):
        """保留末次出现的行：位置表把旧实现的 O(n²) 回查降到 O(n)。"""
        self.progress.emit(0, 3, "正在读取数据...")
        wb = None
        try:
            try:
                wb, it, headers, col_indices = self._open_source()
            except StopIteration:
                self.finished.emit("没有数据")
                return

            if not col_indices:
                self.finished.emit("未找到指定的去重列")
                return

            rows = []
            pos = {}
            dup_count = 0
            for row in it:
                key = self._key(row, col_indices)
                idx = pos.get(key)
                if idx is None:
                    pos[key] = len(rows)
                    rows.append((tuple(row), key))
                else:
                    dup_count += 1
                    # 覆盖首次出现的位置，保持原有行序
                    rows[idx] = (tuple(row), key)
        finally:
            if wb is not None:
                wb.close()

        if dup_count == 0:
            self.finished.emit("没有发现重复数据")
            return

        self.progress.emit(1, 3, f"发现 {dup_count} 行重复，正在生成去重文件...")
        base = os.path.splitext(os.path.basename(self.file_path))[0]
        out_path = os.path.join(self.output_dir, f"{base}_去重结果.xlsx")

        owb = openpyxl.Workbook()
        ows = owb.active
        ows.append(headers)
        for row_data, _ in rows:
            ows.append(row_data)
        owb.save(out_path)
        owb.close()

        summary = f"去重完成！删除了 {dup_count} 行重复数据，保留 {len(rows)} 行"
        self.progress.emit(3, 3, summary)
        self.finished.emit(summary)

    @staticmethod
    def _key(row, col_indices):
        return tuple(row[i] for i in col_indices if i < len(row))
