"""数据筛选功能模块"""
import os
from app.platform_utils import open_file_explorer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QLineEdit, QRadioButton, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names, get_columns
from core.filter_engine import FilterWorker
from app.theme_manager import ThemeManager
from app.widgets.common import get_combo_style, section_label


OPERATORS = [
    ("等于", "eq"),
    ("不等于", "neq"),
    ("大于", "gt"),
    ("小于", "lt"),
    ("大于等于", "gte"),
    ("小于等于", "lte"),
    ("包含", "contains"),
    ("不包含", "not_contains"),
    ("介于", "between"),
    ("为空", "is_empty"),
    ("非空", "not_empty"),
]

OP_LABELS = {op: label for label, op in OPERATORS}


class ConditionRow(QWidget):
    removed = Signal(object)

    def __init__(self, columns: list, idx: int, theme, parent=None):
        super().__init__(parent)
        self._idx = idx
        self._theme = theme
        self._setup_ui(columns)
        self._apply_styles()

    def _setup_ui(self, columns):
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.column_combo = QComboBox()
        self.column_combo.addItems(columns)
        row.addWidget(self.column_combo)

        self.op_combo = QComboBox()
        for label, _ in OPERATORS:
            self.op_combo.addItem(label)
        self.op_combo.currentIndexChanged.connect(self._on_op_changed)
        row.addWidget(self.op_combo)

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("值")
        row.addWidget(self.value_input)

        self.value2_input = QLineEdit()
        self.value2_input.setPlaceholderText("最大值")
        self.value2_input.setVisible(False)
        row.addWidget(self.value2_input)

        del_btn = QPushButton("✕")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self.removed.emit(self))
        row.addWidget(del_btn)

    def _on_op_changed(self):
        op = OPERATORS[self.op_combo.currentIndex()][1]
        self.value2_input.setVisible(op == "between")
        self.value_input.setVisible(op not in ("is_empty", "not_empty"))

    def _apply_styles(self):
        c = self._theme.current_colors
        self.column_combo.setStyleSheet(get_combo_style(c))
        self.op_combo.setStyleSheet(get_combo_style(c))

    def get_condition(self) -> dict | None:
        op = OPERATORS[self.op_combo.currentIndex()][1]
        col = self.column_combo.currentText()
        if not col:
            return None
        if op in ("is_empty", "not_empty"):
            return {"column": col, "operator": op}
        val = self.value_input.text().strip()
        if not val and op != "between":
            return None
        if op == "between":
            val2 = self.value2_input.text().strip()
            if not val or not val2:
                return None
            return {"column": col, "operator": op, "value": val, "value2": val2}
        return {"column": col, "operator": op, "value": val}


class FilterFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: FilterWorker | None = None
        self._file_path = ""
        self._output_dir = ""
        self._theme = ThemeManager.instance()
        self._condition_rows: list[ConditionRow] = []
        self._setup_ui()
        self._apply_styles()
        self._theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, _theme_name: str):
        self._apply_styles()

    def _apply_styles(self):
        c = self._theme.current_colors
        self.file_label.setStyleSheet(f"color: {c['TEXT_MUTED']};")
        self.file_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }}"
        )
        self.sheet_combo.setStyleSheet(get_combo_style(c))
        self.start_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['PRIMARY']}; color: white; border: none; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 10px 40px; font-size: 12pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {c['PRIMARY_HOVER']}; }} "
            f"QPushButton:disabled {{ background-color: {c['TEXT_MUTED']}; }}"
        )
        self.status_label.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-size: 10pt;")
        self.open_dir_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['SUCCESS']}; color: white; border: none; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 10px 28px; font-size: 11pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: #15803D; }}"
        )
        self.add_cond_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; background-color: {c['PRIMARY_LIGHT']}; }}"
        )
        self.logic_and.setStyleSheet(f"color: {c['TEXT_PRIMARY']};")
        self.logic_or.setStyleSheet(f"color: {c['TEXT_PRIMARY']};")
        for cr in self._condition_rows:
            cr._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # ── 选择文件 ──
        layout.addWidget(section_label("选择文件"))
        file_row = QHBoxLayout()
        self.file_btn = QPushButton("选择文件")
        self.file_btn.clicked.connect(self._select_file)
        file_row.addWidget(self.file_btn)
        self.file_label = QLabel("未选择文件")
        file_row.addWidget(self.file_label)
        file_row.addStretch()
        layout.addLayout(file_row)

        # ── Sheet ──
        layout.addWidget(section_label("选择 Sheet"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        layout.addWidget(self.sheet_combo)

        # ── 条件逻辑 ──
        layout.addWidget(section_label("条件逻辑"))
        logic_row = QHBoxLayout()
        self.logic_and = QRadioButton("AND（全部满足）")
        self.logic_or = QRadioButton("OR（任一满足）")
        self.logic_and.setChecked(True)
        logic_row.addWidget(self.logic_and)
        logic_row.addWidget(self.logic_or)
        logic_row.addStretch()
        layout.addLayout(logic_row)

        # ── 条件列表 ──
        layout.addWidget(section_label("筛选条件"))
        self.add_cond_btn = QPushButton("+ 添加条件")
        self.add_cond_btn.clicked.connect(self._add_condition)
        layout.addWidget(self.add_cond_btn)

        self.conditions_area = QVBoxLayout()
        self.conditions_area.setSpacing(6)
        layout.addLayout(self.conditions_area)

        # ── 输出 ──
        layout.addWidget(section_label("输出目录"))
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("默认与源文件相同目录")
        out_row.addWidget(self.output_dir_input)
        out_btn = QPushButton("浏览")
        out_btn.setFixedWidth(60)
        out_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        layout.addStretch()

        # ── 开始按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton("▶  开始筛选")
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_filter)
        btn_row.addWidget(self.start_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── 进度 ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        open_row = QHBoxLayout()
        open_row.addStretch()
        self.open_dir_btn = QPushButton("\U0001F4C2 打开输出目录")
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        open_row.addWidget(self.open_dir_btn)
        open_row.addStretch()
        layout.addLayout(open_row)

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls *.csv);;所有文件 (*)"
        )
        if file_path:
            self._file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.sheet_combo.blockSignals(True)
            self.sheet_combo.clear()
            try:
                sheets = get_sheet_names(file_path)
                self.sheet_combo.addItems(sheets)
                if sheets:
                    self._on_sheet_changed(sheets[0])
            except Exception as e:
                self.file_label.setText(f"读取失败：{e}")
            self.sheet_combo.blockSignals(False)

    def _on_sheet_changed(self, sheet_name: str):
        if not sheet_name or not self._file_path:
            return
        try:
            cols = get_columns(self._file_path, sheet_name)
            self._clear_conditions()
            if cols:
                self._add_condition(cols)
        except Exception:
            pass

    def _add_condition(self, columns: list = None):
        if columns is None and self._file_path:
            sheet = self.sheet_combo.currentText()
            if sheet:
                try:
                    columns = get_columns(self._file_path, sheet)
                except Exception:
                    columns = []
        if not columns:
            return
        row = ConditionRow(columns, len(self._condition_rows), self._theme, self)
        row.removed.connect(self._remove_condition)
        self._condition_rows.append(row)
        self.conditions_area.addWidget(row)

    def _remove_condition(self, row: ConditionRow):
        self._condition_rows.remove(row)
        self.conditions_area.removeWidget(row)
        row.deleteLater()

    def _clear_conditions(self):
        for row in list(self._condition_rows):
            self._remove_condition(row)

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_filter(self):
        sheet = self.sheet_combo.currentText()
        if not self._file_path or not sheet:
            self.status_label.setText("请选择文件和 Sheet")
            return

        conditions = [cr.get_condition() for cr in self._condition_rows]
        conditions = [c for c in conditions if c is not None]
        if not conditions:
            self.status_label.setText("请至少添加一个有效条件")
            return

        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_path)
        self._output_dir = output_dir
        logic = "AND" if self.logic_and.isChecked() else "OR"
        base = os.path.splitext(os.path.basename(self._file_path))[0]
        output_name = f"{base}_筛选结果.xlsx"

        self._worker = FilterWorker(self)
        self._worker.configure(
            file_path=self._file_path, sheet_name=sheet,
            conditions=conditions, logic=logic,
            output_dir=output_dir, output_name=output_name,
        )
        self.start_btn.setEnabled(False)
        self.start_btn.setText("处理中...")
        self.progress_bar.setVisible(True)
        self.open_dir_btn.setVisible(False)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, message: str):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, summary: str):
        c = self._theme.current_colors
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  开始筛选")
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  开始筛选")
        self.status_label.setText(f"❌ 筛选失败：{error_msg}")
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
