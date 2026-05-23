"""透视表功能模块"""
import os
from app.platform_utils import open_file_explorer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QLineEdit, QRadioButton, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names, get_columns
from core.pivoter import PivotWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.widgets.common import get_combo_style, section_label


# Aggregation definitions: (i18n_key, code)
_AGG_DEFS = [
    ("pivot.agg_count", "count"),
    ("pivot.agg_sum", "sum"),
    ("pivot.agg_avg", "avg"),
    ("pivot.agg_min", "min"),
    ("pivot.agg_max", "max"),
]


class PivotFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: PivotWorker | None = None
        self._file_path = ""
        self._output_dir = ""
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._setup_ui()
        self._apply_styles()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)
        self._apply_lang()

    def _on_theme_changed(self, _theme_name: str):
        self._apply_styles()

    def _on_lang_changed(self, _):
        self._apply_lang()

    def _apply_lang(self):
        """Update all user-visible text from current language."""
        self.sec_file.setText(self._lang.tr("label.file"))
        self.file_btn.setText(self._lang.tr("label.select_file"))
        self.file_label.setText(self._lang.tr("label.no_file"))
        self.sec_sheet.setText(self._lang.tr("label.sheet"))
        self.sec_fields.setText(self._lang.tr("pivot.field_settings"))
        self.sec_row.setText(self._lang.tr("pivot.row_field"))
        self.sec_col.setText(self._lang.tr("pivot.col_field"))
        self.sec_value.setText(self._lang.tr("pivot.value_field"))
        self.sec_agg.setText(self._lang.tr("pivot.agg_method"))
        for i, (key, _) in enumerate(_AGG_DEFS):
            if i < len(self._agg_buttons):
                self._agg_buttons[i].setText(self._lang.tr(key))
        self.sec_output.setText(self._lang.tr("label.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("label.default_out_dir"))
        self.out_btn.setText(self._lang.tr("label.browse"))
        self.start_btn.setText(self._lang.tr("pivot.start"))
        self.open_dir_btn.setText(self._lang.tr("common.open_output_dir"))

    def _apply_styles(self):
        c = self._theme.current_colors
        self.file_label.setStyleSheet(f"color: {c['TEXT_MUTED']};")
        self.file_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }}"
        )
        self.sheet_combo.setStyleSheet(get_combo_style(c))
        self.row_combo.setStyleSheet(get_combo_style(c))
        self.col_combo.setStyleSheet(get_combo_style(c))
        self.value_combo.setStyleSheet(get_combo_style(c))
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
        for rb in self._agg_buttons:
            rb.setStyleSheet(f"color: {c['TEXT_PRIMARY']};")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # ── 选择文件 ──
        self.sec_file = section_label("选择文件")
        layout.addWidget(self.sec_file)
        file_row = QHBoxLayout()
        self.file_btn = QPushButton("选择文件")
        self.file_btn.clicked.connect(self._select_file)
        file_row.addWidget(self.file_btn)
        self.file_label = QLabel("未选择文件")
        file_row.addWidget(self.file_label)
        file_row.addStretch()
        layout.addLayout(file_row)

        # ── Sheet ──
        self.sec_sheet = section_label("选择 Sheet")
        layout.addWidget(self.sec_sheet)
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        layout.addWidget(self.sheet_combo)

        # ── 透视字段 ──
        self.sec_fields = section_label("透视字段设置")
        layout.addWidget(self.sec_fields)
        fields_row = QHBoxLayout()
        fields_row.setSpacing(12)

        g1 = QVBoxLayout()
        g1.setSpacing(4)
        self.sec_row = section_label("行字段")
        g1.addWidget(self.sec_row)
        self.row_combo = QComboBox()
        g1.addWidget(self.row_combo)
        fields_row.addLayout(g1)

        g2 = QVBoxLayout()
        g2.setSpacing(4)
        self.sec_col = section_label("列字段")
        g2.addWidget(self.sec_col)
        self.col_combo = QComboBox()
        g2.addWidget(self.col_combo)
        fields_row.addLayout(g2)

        g3 = QVBoxLayout()
        g3.setSpacing(4)
        self.sec_value = section_label("值字段")
        g3.addWidget(self.sec_value)
        self.value_combo = QComboBox()
        g3.addWidget(self.value_combo)
        fields_row.addLayout(g3)

        layout.addLayout(fields_row)

        # ── 聚合方式 ──
        self.sec_agg = section_label("聚合方式")
        layout.addWidget(self.sec_agg)
        agg_row = QHBoxLayout()
        self._agg_buttons = []
        for i, (key, _) in enumerate(_AGG_DEFS):
            rb = QRadioButton(key)  # placeholder, _apply_lang replaces
            if i == 0:
                rb.setChecked(True)
            agg_row.addWidget(rb)
            self._agg_buttons.append(rb)
        agg_row.addStretch()
        layout.addLayout(agg_row)

        # ── 输出 ──
        self.sec_output = section_label("输出目录")
        layout.addWidget(self.sec_output)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("默认与源文件相同目录")
        out_row.addWidget(self.output_dir_input)
        self.out_btn = QPushButton("浏览")
        self.out_btn.setFixedWidth(60)
        self.out_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.out_btn)
        layout.addLayout(out_row)

        layout.addStretch()

        # ── 开始按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton("▶  生成透视表")
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_pivot)
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
            self, self._lang.tr("label.file_dialog"), "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
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
                self.file_label.setText(self._lang.tr("label.read_error", error=str(e)))
            self.sheet_combo.blockSignals(False)

    def _on_sheet_changed(self, sheet_name: str):
        if not sheet_name or not self._file_path:
            return
        try:
            cols = get_columns(self._file_path, sheet_name)
            for combo in [self.row_combo, self.col_combo, self.value_combo]:
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(cols)
                combo.blockSignals(False)
        except Exception:
            pass

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("label.dir_dialog"))
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_pivot(self):
        sheet = self.sheet_combo.currentText()
        if not self._file_path or not sheet:
            self.status_label.setText(self._lang.tr("label.select_file_and_sheet"))
            return

        row_f = self.row_combo.currentText()
        col_f = self.col_combo.currentText()
        val_f = self.value_combo.currentText()
        if not row_f or not col_f or not val_f:
            self.status_label.setText(self._lang.tr("pivot.select_fields"))
            return

        agg = "count"
        for i, rb in enumerate(self._agg_buttons):
            if rb.isChecked():
                agg = _AGG_DEFS[i][1]
                break

        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_path)
        self._output_dir = output_dir
        base = os.path.splitext(os.path.basename(self._file_path))[0]
        output_name = f"{base}_透视表.xlsx"

        self._worker = PivotWorker(self)
        self._worker.configure(
            file_path=self._file_path, sheet_name=sheet,
            row_field=row_f, col_field=col_f, value_field=val_f,
            agg_func=agg, output_dir=output_dir, output_name=output_name,
        )
        self.start_btn.setEnabled(False)
        self.start_btn.setText(self._lang.tr("common.processing"))
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
        self.start_btn.setText(self._lang.tr("pivot.start"))
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("pivot.start"))
        self.status_label.setText(self._lang.tr("pivot.error_failed", error=error_msg))
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
