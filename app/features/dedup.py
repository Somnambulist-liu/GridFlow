"""去重功能模块"""
import os
from app.platform_utils import open_file_explorer
from app.settings import get_default_output_dir, get_auto_open_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QRadioButton, QLineEdit,
    QListWidget, QAbstractItemView, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names, get_columns
from core.deduper import DedupWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.widgets.common import get_combo_style, section_label


class DedupFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: DedupWorker | None = None
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
        self._file_section_label.setText(self._lang.tr("dedup.select_file"))
        self.file_btn.setText(self._lang.tr("dedup.select_file"))
        self._sheet_section_label.setText(self._lang.tr("dedup.select_sheet"))
        self._column_section_label.setText(self._lang.tr("dedup.dedup_columns"))
        self._keep_section_label.setText(self._lang.tr("dedup.keep_mode"))
        self.keep_first.setText(self._lang.tr("dedup.keep_first"))
        self.keep_last.setText(self._lang.tr("dedup.keep_last"))
        self._output_section_label.setText(self._lang.tr("dedup.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("dedup.output_dir_placeholder"))
        self.out_browse_btn.setText(self._lang.tr("label.browse"))
        self.start_btn.setText(self._lang.tr("dedup.start_btn"))
        self.open_dir_btn.setText(self._lang.tr("common.open_output_dir"))
        # file_label is dynamic — update based on stored state
        self._update_file_label()

    def _apply_styles(self):
        c = self._theme.current_colors
        self.file_label.setStyleSheet(f"color: {c['TEXT_MUTED']};")
        self.file_btn.setStyleSheet(self._btn_style())
        self.sheet_combo.setStyleSheet(get_combo_style(c))
        self.column_list.setStyleSheet(f"QListWidget {{ border: 1px solid {c['BORDER']}; border-radius: 4px; color: {c['TEXT_PRIMARY']}; background-color: {c['BG_CARD']}; }}")
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

        # ── 选择文件 ──
        self._file_section_label = section_label("")
        layout.addWidget(self._file_section_label)
        file_row = QHBoxLayout()
        self.file_btn = QPushButton()
        self.file_btn.clicked.connect(self._select_file)
        file_row.addWidget(self.file_btn)
        self.file_label = QLabel()
        self.file_label.setText(self._lang.tr("dedup.no_file"))
        file_row.addWidget(self.file_label)
        file_row.addStretch()
        layout.addLayout(file_row)

        # ── Sheet + 列 ──
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        g1 = QVBoxLayout()
        g1.setSpacing(4)
        self._sheet_section_label = section_label("")
        g1.addWidget(self._sheet_section_label)
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        g1.addWidget(self.sheet_combo)
        row1.addLayout(g1)
        layout.addLayout(row1)

        self._column_section_label = section_label("")
        layout.addWidget(self._column_section_label)
        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.column_list.setMaximumHeight(100)
        layout.addWidget(self.column_list)

        # ── 保留选项 ──
        self._keep_section_label = section_label("")
        layout.addWidget(self._keep_section_label)
        keep_row = QHBoxLayout()
        self.keep_first = QRadioButton()
        self.keep_last = QRadioButton()
        self.keep_first.setChecked(True)
        keep_row.addWidget(self.keep_first)
        keep_row.addWidget(self.keep_last)
        keep_row.addStretch()
        layout.addLayout(keep_row)

        # ── 输出 ──
        self._output_section_label = section_label("")
        layout.addWidget(self._output_section_label)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        default_dir = get_default_output_dir()
        if default_dir:
            self.output_dir_input.setText(default_dir)
        out_row.addWidget(self.output_dir_input)
        self.out_browse_btn = QPushButton()
        self.out_browse_btn.setFixedWidth(60)
        self.out_browse_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.out_browse_btn)
        layout.addLayout(out_row)

        layout.addStretch()

        # ── 开始按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton()
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_dedup)
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
        self.open_dir_btn = QPushButton()
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        open_row.addWidget(self.open_dir_btn)
        open_row.addStretch()
        layout.addLayout(open_row)

    def _update_file_label(self):
        """Update file_label text based on stored state."""
        if self._file_path:
            self.file_label.setText(os.path.basename(self._file_path))
        else:
            self.file_label.setText(self._lang.tr("dedup.no_file"))

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._lang.tr("dedup.dialog_select_excel"), "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        if file_path:
            self._file_path = file_path
            self._update_file_label()
            self.sheet_combo.blockSignals(True)
            self.sheet_combo.clear()
            try:
                sheets = get_sheet_names(file_path)
                self.sheet_combo.addItems(sheets)
                if sheets:
                    self._on_sheet_changed(sheets[0])
            except Exception as e:
                self.file_label.setText(self._lang.tr("dedup.read_error", error=str(e)))
            self.sheet_combo.blockSignals(False)

    def _on_sheet_changed(self, sheet_name: str):
        if not sheet_name or not self._file_path:
            return
        try:
            cols = get_columns(self._file_path, sheet_name)
            self.column_list.clear()
            self.column_list.addItems(cols)
            for i in range(self.column_list.count()):
                self.column_list.item(i).setSelected(True)
        except Exception:
            pass

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("dedup.dialog_select_output"))
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_dedup(self):
        sheet = self.sheet_combo.currentText()
        if not self._file_path or not sheet:
            self.status_label.setText(self._lang.tr("dedup.need_file_and_sheet"))
            return
        columns = [self.column_list.item(i).text() for i in range(self.column_list.count()) if self.column_list.item(i).isSelected()]
        if not columns:
            self.status_label.setText(self._lang.tr("dedup.need_columns"))
            return
        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_path)
        self._output_dir = output_dir
        keep = "first" if self.keep_first.isChecked() else "last"

        self._worker = DedupWorker(self)
        self._worker.configure(
            file_path=self._file_path, sheet_name=sheet,
            columns=columns, keep=keep, output_dir=output_dir,
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
        self.start_btn.setText(self._lang.tr("dedup.start_btn"))
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)
        if get_auto_open_dir():
            self._open_output_dir()

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("dedup.start_btn"))
        self.status_label.setText(self._lang.tr("dedup.error_fmt", error=error_msg))
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
