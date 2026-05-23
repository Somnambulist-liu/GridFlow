"""合并功能模块"""
import os
from app.platform_utils import open_file_explorer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QRadioButton, QLineEdit, QListWidget,
    QAbstractItemView, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names
from core.merger import MergeWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.widgets.common import section_label


class MergeFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: MergeWorker | None = None
        self._file_paths = []
        self._file_path = ""
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
        self._mode_section_label.setText(self._lang.tr("merge.mode"))
        self.mode_files.setText(self._lang.tr("merge.mode_files"))
        self.mode_sheets.setText(self._lang.tr("merge.mode_sheets"))
        self._files_section_label.setText(self._lang.tr("merge.select_files"))
        self.add_files_btn.setText(self._lang.tr("merge.add_files"))
        self.clear_files_btn.setText(self._lang.tr("merge.clear"))
        self._sheet_file_section_label.setText(self._lang.tr("merge.select_file"))
        self.sheet_file_btn.setText(self._lang.tr("merge.select_file"))
        self._sheets_select_label.setText(self._lang.tr("merge.select_sheets"))
        self._output_section_label.setText(self._lang.tr("merge.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("merge.output_dir_placeholder"))
        self.output_browse_btn.setText(self._lang.tr("label.browse"))
        self._output_name_label.setText(self._lang.tr("merge.output_name"))
        self.start_btn.setText(self._lang.tr("merge.start_btn"))
        self.open_dir_btn.setText(self._lang.tr("common.open_output_dir"))
        # sheet_file_label is dynamic — handled by _update_sheet_file_label

    def _apply_styles(self):
        c = self._theme.current_colors
        self.file_list.setStyleSheet(f"QListWidget {{ border: 1px solid {c['BORDER']}; border-radius: 4px; color: {c['TEXT_PRIMARY']}; background-color: {c['BG_CARD']}; }}")
        self.sheet_list.setStyleSheet(f"QListWidget {{ border: 1px solid {c['BORDER']}; border-radius: 4px; color: {c['TEXT_PRIMARY']}; background-color: {c['BG_CARD']}; }}")
        self.sheet_file_label.setStyleSheet(f"color: {c['TEXT_MUTED']};")
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
        btn_style = self._btn_style()
        self.add_files_btn.setStyleSheet(btn_style)
        self.clear_files_btn.setStyleSheet(btn_style)
        self.sheet_file_btn.setStyleSheet(btn_style)
        self.output_browse_btn.setStyleSheet(btn_style)

    def _btn_style(self) -> str:
        c = self._theme.current_colors
        return (
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }}"
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # ── 合并模式 ──
        self._mode_section_label = section_label("")
        layout.addWidget(self._mode_section_label)
        mode_row = QHBoxLayout()
        self.mode_files = QRadioButton()
        self.mode_sheets = QRadioButton()
        self.mode_files.setChecked(True)
        self.mode_files.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_files)
        mode_row.addWidget(self.mode_sheets)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ── 文件选择区 ──
        self.files_area = QWidget()
        files_layout = QVBoxLayout(self.files_area)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(6)
        self._files_section_label = section_label("")
        files_layout.addWidget(self._files_section_label)
        btn_row = QHBoxLayout()
        self.add_files_btn = QPushButton()
        self.add_files_btn.clicked.connect(self._add_files)
        btn_row.addWidget(self.add_files_btn)
        self.clear_files_btn = QPushButton()
        self.clear_files_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self.clear_files_btn)
        btn_row.addStretch()
        files_layout.addLayout(btn_row)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(100)
        files_layout.addWidget(self.file_list)
        layout.addWidget(self.files_area)

        # ── Sheet 选择区 ──
        self.sheets_area = QWidget()
        sheets_layout = QVBoxLayout(self.sheets_area)
        sheets_layout.setContentsMargins(0, 0, 0, 0)
        sheets_layout.setSpacing(6)
        self._sheet_file_section_label = section_label("")
        sheets_layout.addWidget(self._sheet_file_section_label)
        sf_row = QHBoxLayout()
        self.sheet_file_btn = QPushButton()
        self.sheet_file_btn.clicked.connect(self._select_file_for_sheets)
        sf_row.addWidget(self.sheet_file_btn)
        self.sheet_file_label = QLabel()
        sf_row.addWidget(self.sheet_file_label)
        sf_row.addStretch()
        sheets_layout.addLayout(sf_row)
        self._sheets_select_label = section_label("")
        sheets_layout.addWidget(self._sheets_select_label)
        self.sheet_list = QListWidget()
        self.sheet_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sheet_list.setMaximumHeight(100)
        sheets_layout.addWidget(self.sheet_list)
        self.sheets_area.setVisible(False)
        layout.addWidget(self.sheets_area)

        # ── 输出 ──
        self._output_section_label = section_label("")
        layout.addWidget(self._output_section_label)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        out_row.addWidget(self.output_dir_input)
        self.output_browse_btn = QPushButton()
        self.output_browse_btn.setFixedWidth(60)
        self.output_browse_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.output_browse_btn)
        layout.addLayout(out_row)

        name_row = QHBoxLayout()
        self._output_name_label = section_label("")
        name_row.addWidget(self._output_name_label)
        self.output_name_input = QLineEdit("合并结果.xlsx")
        self.output_name_input.setFixedWidth(250)
        name_row.addWidget(self.output_name_input)
        name_row.addStretch()
        layout.addLayout(name_row)

        layout.addStretch()

        # ── 开始按钮 ──
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        self.start_btn = QPushButton()
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_merge)
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

        # ── 打开目录 ──
        open_row = QHBoxLayout()
        open_row.addStretch()
        self.open_dir_btn = QPushButton()
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        open_row.addWidget(self.open_dir_btn)
        open_row.addStretch()
        layout.addLayout(open_row)

        # Set initial sheet_file_label to no-file state
        self.sheet_file_label.setText(self._lang.tr("merge.no_file"))

    def _on_mode_changed(self):
        is_files = self.mode_files.isChecked()
        self.files_area.setVisible(is_files)
        self.sheets_area.setVisible(not is_files)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, self._lang.tr("merge.dialog_select_excel"), "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        for p in paths:
            if p not in self._file_paths:
                self._file_paths.append(p)
                self.file_list.addItem(os.path.basename(p))

    def _clear_files(self):
        self._file_paths.clear()
        self.file_list.clear()

    def _select_file_for_sheets(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._lang.tr("merge.dialog_select_excel"), "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        if file_path:
            self._file_path = file_path
            self.sheet_file_label.setText(os.path.basename(file_path))
            self.sheet_list.clear()
            try:
                sheets = get_sheet_names(file_path)
                self.sheet_list.addItems(sheets)
                for i in range(self.sheet_list.count()):
                    self.sheet_list.item(i).setSelected(True)
            except Exception as e:
                self.sheet_file_label.setText(self._lang.tr("merge.read_error", error=str(e)))

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("merge.dialog_select_output"))
        if dir_path:
            self.output_dir_input.setText(dir_path)
            self._output_dir = dir_path

    def _start_merge(self):
        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_paths[0] if self._file_paths else self._file_path or ".")
        output_name = self.output_name_input.text().strip() or "合并结果.xlsx"
        if not output_name.endswith(".xlsx"):
            output_name += ".xlsx"
        self._output_dir = output_dir

        self._worker = MergeWorker(self)
        if self.mode_files.isChecked():
            if len(self._file_paths) < 2:
                self.status_label.setText(self._lang.tr("merge.need_two_files"))
                return
            self._worker.configure(
                mode="files", file_paths=self._file_paths,
                output_dir=output_dir, output_name=output_name,
            )
        else:
            selected = [self.sheet_list.item(i).text() for i in range(self.sheet_list.count()) if self.sheet_list.item(i).isSelected()]
            if not selected or not self._file_path:
                self.status_label.setText(self._lang.tr("merge.need_file_and_sheet"))
                return
            self._worker.configure(
                mode="sheets", file_path=self._file_path,
                sheet_names=selected, output_dir=output_dir, output_name=output_name,
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
        self.start_btn.setText(self._lang.tr("merge.start_btn"))
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("merge.start_btn"))
        self.status_label.setText(self._lang.tr("merge.error_fmt", error=error_msg))
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
