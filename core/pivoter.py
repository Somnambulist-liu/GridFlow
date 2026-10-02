"""透视表引擎"""
import os
from openpyxl import load_workbook, Workbook
from PySide6.QtCore import QThread, Signal


class PivotWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(str)
    error_occurred = Signal(str)

    # 累加器下标
    _COUNT, _SUM, _NUM, _MIN, _MAX = 0, 1, 2, 3, 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = ""
        self._sheet_name = ""
        self._row_field = ""
        self._col_field = ""
        self._value_field = ""
        self._agg_func = "count"
        self._output_dir = ""
        self._output_name = ""

    def configure(self, file_path: str, sheet_name: str,
                  row_field: str, col_field: str, value_field: str,
                  agg_func: str = "count", output_dir: str = "",
                  output_name: str = "透视表结果.xlsx"):
        self._file_path = file_path
        self._sheet_name = sheet_name
        self._row_field = row_field
        self._col_field = col_field
        self._value_field = value_field
        self._agg_func = agg_func
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
                except StopIteration:
                    self.finished.emit("数据不足（至少需要标题行 + 1 行数据）")
                    return
                if not headers:
                    self.finished.emit("数据不足（至少需要标题行 + 1 行数据）")
                    return

                col_idx = {h: i for i, h in enumerate(headers)}

                # 与旧实现一致：先判“数据不足”，再报字段不存在（缺字段时只计行数）
                missing = next((f for f in (self._row_field, self._col_field,
                                            self._value_field) if f not in col_idx), None)
                row_field_idx = col_idx.get(self._row_field)
                col_field_idx = col_idx.get(self._col_field)
                val_idx = col_idx.get(self._value_field)

                # 单趟扫描 + 增量聚合：内存只与“行值 × 列值”组合数相关，
                # 不再把每一格的值都存进列表（旧实现按值分组缓存全部原始值）。
                expected = getattr(ws, "max_row", None)
                expected = expected - 1 if expected else 0
                stats = {}
                total = 0
                for row in it:
                    total += 1
                    if total % 1000 == 0:
                        self.progress.emit(total, expected or total, f"正在汇总 {total} 行...")
                    if missing is not None:
                        continue
                    row_value = row[row_field_idx]
                    col_value = row[col_field_idx]
                    rv = str(row_value) if row_value is not None else "(空)"
                    cv = str(col_value) if col_value is not None else "(空)"
                    acc = stats.get((rv, cv))
                    if acc is None:
                        acc = stats[(rv, cv)] = [0, 0.0, 0, None, None]
                    acc[self._COUNT] += 1
                    try:
                        number = float(row[val_idx])
                    except (ValueError, TypeError):
                        continue
                    acc[self._SUM] += number
                    acc[self._NUM] += 1
                    if acc[self._MIN] is None or number < acc[self._MIN]:
                        acc[self._MIN] = number
                    if acc[self._MAX] is None or number > acc[self._MAX]:
                        acc[self._MAX] = number
            finally:
                wb.close()

            if total == 0:
                self.finished.emit("数据不足（至少需要标题行 + 1 行数据）")
                return
            if missing is not None:
                raise ValueError(f"列 '{missing}' 不存在")

            agg_results = {key: self._finalize(acc) for key, acc in stats.items()}

            # Compute aggregation
            row_vals = sorted(set(k[0] for k in stats))
            col_vals = sorted(set(k[1] for k in stats))

            # Write cross-tabulation
            output_path = os.path.join(self._output_dir, self._output_name)
            out_wb = Workbook()
            out_ws = out_wb.active

            header_row = [f"{self._row_field} \\ {self._col_field}"] + [str(c) for c in col_vals] + ["合计"]
            out_ws.append(header_row)

            for rv in row_vals:
                out_row = [str(rv)]
                row_total = 0
                for cv in col_vals:
                    val = agg_results.get((rv, cv), 0)
                    out_row.append(val)
                    row_total += val if isinstance(val, (int, float)) else 0
                out_row.append(row_total)
                out_ws.append(out_row)

            # Totals row
            total_row = ["合计"]
            for j, cv in enumerate(col_vals):
                col_total = sum(
                    agg_results.get((rv, cv), 0)
                    for rv in row_vals
                    if isinstance(agg_results.get((rv, cv), 0), (int, float))
                )
                total_row.append(col_total)
            grand_total = sum(v for v in total_row[1:] if isinstance(v, (int, float)))
            total_row.append(grand_total)
            out_ws.append(total_row)

            out_wb.save(output_path)
            out_wb.close()

            self.progress.emit(total, total, "完成")
            self.finished.emit(
                f"透视表生成完成！{len(row_vals)} 行 × {len(col_vals)} 列\n"
                f"输出文件：{os.path.basename(output_path)}"
            )

        except Exception as e:
            self.error_occurred.emit(str(e))

    def _finalize(self, acc: list):
        """把累加器换算成与旧实现 _aggregate 完全一致的聚合结果。"""
        count, number_sum, number_count, minimum, maximum = acc
        if self._agg_func == "count":
            return count
        elif self._agg_func == "sum":
            return round(number_sum, 2)
        elif self._agg_func == "avg":
            return round(number_sum / number_count, 2) if number_count else 0
        elif self._agg_func == "min":
            return minimum if minimum is not None else 0
        elif self._agg_func == "max":
            return maximum if maximum is not None else 0
        return count

    def _aggregate(self, values: list):
        """保留旧接口：按原始值列表聚合（少量数据或外部调用）。"""
        numeric = []
        for v in values:
            try:
                numeric.append(float(v))
            except (ValueError, TypeError):
                pass

        if self._agg_func == "count":
            return len(values)
        elif self._agg_func == "sum":
            return round(sum(numeric), 2)
        elif self._agg_func == "avg":
            return round(sum(numeric) / len(numeric), 2) if numeric else 0
        elif self._agg_func == "min":
            return min(numeric) if numeric else 0
        elif self._agg_func == "max":
            return max(numeric) if numeric else 0
        return len(values)
