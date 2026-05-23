"""数据校验功能模块"""
import os
from app.platform_utils import open_file_explorer
from app.settings import get_default_output_dir, get_auto_open_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QCheckBox, QLineEdit, QSpinBox,
    QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names
from core.validator import ValidateWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.widgets.common import get_combo_style, section_label


class ValidateFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ValidateWorker | None = None
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
        self.sec_checks.setText(self._lang.tr("validate.check_types"))
        self.chk_empty.setText(self._lang.tr("validate.empty_check"))
        self.empty_threshold_label.setText(self._lang.tr("validate.threshold_label"))
        self.chk_outliers.setText(self._lang.tr("validate.outlier_check"))
        self.iqr_label.setText(self._lang.tr("validate.iqr_label"))
        self.chk_type.setText(self._lang.tr("validate.type_check"))
        self.chk_dup.setText(self._lang.tr("validate.dup_check"))
        self.sec_output.setText(self._lang.tr("label.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("label.default_out_dir"))
        self.out_btn.setText(self._lang.tr("label.browse"))
        self.start_btn.setText(self._lang.tr("validate.start"))
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
        for cb in self._checkboxes:
            cb.setStyleSheet(f"color: {c['TEXT_PRIMARY']};")

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
        layout.addWidget(self.sheet_combo)

        # ── 校验类型 ──
        self.sec_checks = section_label("校验类型")
        layout.addWidget(self.sec_checks)
        self._checkboxes = []

        self.chk_empty = QCheckBox("空值检测（列空值率超过阈值）")
        self._checkboxes.append(self.chk_empty)
        layout.addWidget(self.chk_empty)

        empty_row = QHBoxLayout()
        empty_row.setSpacing(8)
        self.empty_threshold_label = QLabel("阈值 (%):")
        empty_row.addWidget(self.empty_threshold_label)
        self.empty_threshold = QSpinBox()
        self.empty_threshold.setRange(1, 100)
        self.empty_threshold.setValue(50)
        empty_row.addWidget(self.empty_threshold)
        empty_row.addStretch()
        layout.addLayout(empty_row)

        self.chk_outliers = QCheckBox("异常值检测（IQR 四分位距法）")
        self._checkboxes.append(self.chk_outliers)
        layout.addWidget(self.chk_outliers)

        iqr_row = QHBoxLayout()
        iqr_row.setSpacing(8)
        self.iqr_label = QLabel("IQR 倍数:")
        iqr_row.addWidget(self.iqr_label)
        self.outlier_multiplier = QSpinBox()
        self.outlier_multiplier.setRange(1, 5)
        self.outlier_multiplier.setValue(1)
        self.outlier_multiplier.setSuffix(".5")
        iqr_row.addWidget(self.outlier_multiplier)
        iqr_row.addStretch()
        layout.addLayout(iqr_row)

        self.chk_type = QCheckBox("类型一致性检查（混合 string/number 检测）")
        self._checkboxes.append(self.chk_type)
        layout.addWidget(self.chk_type)

        self.chk_dup = QCheckBox("重复行检测")
        self._checkboxes.append(self.chk_dup)
        layout.addWidget(self.chk_dup)

        # ── 输出 ──
        self.sec_output = section_label("输出目录")
        layout.addWidget(self.sec_output)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        default_dir = get_default_output_dir()
        if default_dir:
            self.output_dir_input.setText(default_dir)
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
        self.start_btn = QPushButton("▶  开始校验")
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_validate)
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
        self.status_label.setMinimumHeight(100)
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
            except Exception as e:
                self.file_label.setText(self._lang.tr("label.read_error", error=str(e)))
            self.sheet_combo.blockSignals(False)

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("label.dir_dialog"))
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_validate(self):
        sheet = self.sheet_combo.currentText()
        if not self._file_path or not sheet:
            self.status_label.setText(self._lang.tr("label.select_file_and_sheet"))
            return

        checks = {
            "empty": self.chk_empty.isChecked(),
            "empty_threshold": self.empty_threshold.value(),
            "outliers": self.chk_outliers.isChecked(),
            "outlier_multiplier": 1.5,
            "type_check": self.chk_type.isChecked(),
            "duplicates": self.chk_dup.isChecked(),
        }

        if not any([checks["empty"], checks["outliers"], checks["type_check"], checks["duplicates"]]):
            self.status_label.setText(self._lang.tr("validate.select_one"))
            return

        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_path)
        self._output_dir = output_dir

        self._worker = ValidateWorker(self)
        self._worker.configure(
            file_path=self._file_path, sheet_name=sheet,
            checks=checks, output_dir=output_dir,
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
        self.start_btn.setText(self._lang.tr("validate.start"))
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(
            f"color: {c['TEXT_PRIMARY']}; font-size: 10pt; "
            f"background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: 4px; padding: 8px;"
        )
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)
        if get_auto_open_dir():
            self._open_output_dir()

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("validate.start"))
        self.status_label.setText(self._lang.tr("validate.error_failed", error=error_msg))
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
