"""列操作引擎"""
import os
from openpyxl import load_workbook
from PySide6.QtCore import QThread, Signal

from core.reader import StreamedWorkbook


class ColumnOpsWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = ""
        self._sheet_name = ""
        self._kept_columns = []
        self._renames = {}
        self._order = []
        self._calc_columns = []
        self._output_dir = ""
        self._output_name = ""

    def configure(self, file_path: str, sheet_name: str,
                  kept_columns: list, renames: dict, order: list,
                  calc_columns: list, output_dir: str = "",
                  output_name: str = "列操作结果.xlsx"):
        self._file_path = file_path
        self._sheet_name = sheet_name
        self._kept_columns = kept_columns
        self._renames = renames
        self._order = order
        self._calc_columns = calc_columns
        self._output_dir = output_dir
        self._output_name = output_name

    def run(self):
        try:
            wb = load_workbook(self._file_path, read_only=True)
            try:
                ws = wb[self._sheet_name]
                it = ws.iter_rows(values_only=True)

                try:
                    headers = list(next(it))
                    header_count = 1
                except StopIteration:
                    headers = []
                    header_count = 0

                header_index = {h: i for i, h in enumerate(headers)}

                # Determine final column order
                final_cols = self._order if self._order else self._kept_columns
                final_headers = [self._renames.get(c, c) for c in final_cols]
                for calc in self._calc_columns:
                    final_headers.append(calc["name"])

                expected = getattr(ws, "max_row", None)
                expected = expected - 1 if expected else 0

                # 流式处理：逐行转换并直接写入 write_only 工作簿
                with StreamedWorkbook() as out:
                    out_ws = out.sheet()
                    out_ws.append(final_headers)

                    row_idx = 0
                    for row in it:
                        row_idx += 1
                        if row_idx % 500 == 0:
                            self.progress.emit(row_idx, expected or row_idx,
                                               f"正在处理 {row_idx}/{expected or row_idx} 行...")

                        out_row = []
                        for col in final_cols:
                            if col in header_index:
                                out_row.append(row[header_index[col]])
                            else:
                                out_row.append("")

                        for calc in self._calc_columns:
                            try:
                                expr = calc["expression"]
                                for col in header_index:
                                    expr = expr.replace("{" + col + "}", str(row[header_index[col]] or 0))
                                result = float(eval(expr))
                                out_row.append(round(result, 2) if result != int(result) else int(result))
                            except Exception:
                                out_row.append("")

                        out_ws.append(out_row)

                    total_rows = header_count + row_idx - 1
                    output_path = os.path.join(self._output_dir, self._output_name)
                    out.save(output_path)
            finally:
                wb.close()

            self.progress.emit(max(total_rows, 0), max(total_rows, 0), "完成")
            self.finished.emit(
                f"列操作完成！{len(final_headers)} 列 × {total_rows} 行\n输出文件：{os.path.basename(output_path)}"
            )

        except Exception as e:
            self.error_occurred.emit(str(e))
