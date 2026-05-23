"""格式转换功能模块"""
import os
from app.platform_utils import open_file_explorer
from app.settings import get_default_output_dir, get_auto_open_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QRadioButton, QLineEdit, QListWidget, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.converter import ConvertWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.widgets.common import section_label


class ConvertFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ConvertWorker | None = None
        self._file_paths = []
        self._output_dir = ""
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)
        self._setup_ui()
        self._apply_styles()
        self._apply_lang()

    def _on_theme_changed(self, _theme_name: str):
        self._apply_styles()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def _apply_lang(self):
        """Update all user-visible text from current language."""
        self._fmt_section_label.setText(self._lang.tr("convert.target_format"))
        self.fmt_xlsx_to_csv.setText(self._lang.tr("convert.fmt_xlsx_to_csv"))
        self.fmt_csv_to_xlsx.setText(self._lang.tr("convert.fmt_csv_to_xlsx"))
        self._files_section_label.setText(self._lang.tr("convert.select_files"))
        self.add_btn.setText(self._lang.tr("convert.add_files"))
        self.clear_btn.setText(self._lang.tr("convert.clear"))
        self._output_section_label.setText(self._lang.tr("convert.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("convert.output_dir_placeholder"))
        self.output_browse_btn.setText(self._lang.tr("label.browse"))
        self.start_btn.setText(self._lang.tr("convert.start_btn"))
        self.open_dir_btn.setText(self._lang.tr("common.open_output_dir"))

    def _apply_styles(self):
        c = self._theme.current_colors
        self.file_list.setStyleSheet(f"QListWidget {{ border: 1px solid {c['BORDER']}; border-radius: 4px; color: {c['TEXT_PRIMARY']}; background-color: {c['BG_CARD']}; }}")
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
        self.add_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }}"
        )
        self.clear_btn.setStyleSheet(self.add_btn.styleSheet())
        self.output_browse_btn.setStyleSheet(self.add_btn.styleSheet())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # ── 目标格式 ──
        self._fmt_section_label = section_label("")
        layout.addWidget(self._fmt_section_label)
        fmt_row = QHBoxLayout()
        self.fmt_xlsx_to_csv = QRadioButton()
        self.fmt_csv_to_xlsx = QRadioButton()
        self.fmt_xlsx_to_csv.setChecked(True)
        fmt_row.addWidget(self.fmt_xlsx_to_csv)
        fmt_row.addWidget(self.fmt_csv_to_xlsx)
        fmt_row.addStretch()
        layout.addLayout(fmt_row)

        # ── 文件选择 ──
        self._files_section_label = section_label("")
        layout.addWidget(self._files_section_label)
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton()
        self.add_btn.clicked.connect(self._add_files)
        btn_row.addWidget(self.add_btn)
        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(100)
        layout.addWidget(self.file_list)

        # ── 输出目录 ──
        self._output_section_label = section_label("")
        layout.addWidget(self._output_section_label)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        default_dir = get_default_output_dir()
        if default_dir:
            self.output_dir_input.setText(default_dir)
        out_row.addWidget(self.output_dir_input)
        self.output_browse_btn = QPushButton()
        self.output_browse_btn.setFixedWidth(60)
        self.output_browse_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.output_browse_btn)
        layout.addLayout(out_row)

        layout.addStretch()

        # ── 开始按钮 ──
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        self.start_btn = QPushButton()
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_convert)
        btn_row2.addWidget(self.start_btn)
        btn_row2.addStretch()
        layout.addLayout(btn_row2)

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
        self.open_dir_btn = QPushButton()
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        open_row.addWidget(self.open_dir_btn)
        open_row.addStretch()
        layout.addLayout(open_row)

    def _add_files(self):
        is_csv = self.fmt_csv_to_xlsx.isChecked()
        filter_str = "CSV 文件 (*.csv);;所有文件 (*)" if is_csv else "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        paths, _ = QFileDialog.getOpenFileNames(self, self._lang.tr("convert.dialog_select_files"), "", filter_str)
        for p in paths:
            if p not in self._file_paths:
                self._file_paths.append(p)
                self.file_list.addItem(os.path.basename(p))

    def _clear_files(self):
        self._file_paths.clear()
        self.file_list.clear()

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("convert.dialog_select_output"))
        if dir_path:
            self.output_dir_input.setText(dir_path)
            self._output_dir = dir_path

    def _start_convert(self):
        if not self._file_paths:
            self.status_label.setText(self._lang.tr("convert.need_files"))
            return
        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_paths[0])
        self._output_dir = output_dir
        target = "csv" if self.fmt_xlsx_to_csv.isChecked() else "xlsx"

        self._worker = ConvertWorker(self)
        self._worker.configure(
            file_paths=self._file_paths,
            target_format=target,
            output_dir=output_dir,
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
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, summary: str):
        c = self._theme.current_colors
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("convert.start_btn"))
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)
        if get_auto_open_dir():
            self._open_output_dir()

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("convert.start_btn"))
        self.status_label.setText(self._lang.tr("convert.error_fmt", error=error_msg))
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
