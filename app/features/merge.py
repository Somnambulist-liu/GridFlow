"""合并功能模块"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QRadioButton, QLineEdit, QListWidget,
    QAbstractItemView, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names
from core.merger import MergeWorker
from app.theme import (
    PRIMARY, PRIMARY_HOVER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, BG_CARD, BG_INPUT, RADIUS_SM,
)
from app.widgets.common import COMBO_STYLE, section_label


class MergeFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: MergeWorker | None = None
        self._file_paths = []
        self._file_path = ""
        self._output_dir = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # ── 合并模式 ──
        layout.addWidget(section_label("合并模式"))
        mode_row = QHBoxLayout()
        self.mode_files = QRadioButton("多文件合并")
        self.mode_sheets = QRadioButton("多 Sheet 合并")
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
        files_layout.addWidget(section_label("选择文件（可多选）"))
        btn_row = QHBoxLayout()
        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.setStyleSheet(self._btn_style())
        self.add_files_btn.clicked.connect(self._add_files)
        btn_row.addWidget(self.add_files_btn)
        self.clear_files_btn = QPushButton("清空")
        self.clear_files_btn.setStyleSheet(self._btn_style())
        self.clear_files_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self.clear_files_btn)
        btn_row.addStretch()
        files_layout.addLayout(btn_row)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(100)
        self.file_list.setStyleSheet(f"QListWidget {{ border: 1px solid {BORDER}; border-radius: 4px; }}")
        files_layout.addWidget(self.file_list)
        layout.addWidget(self.files_area)

        # ── Sheet 选择区 ──
        self.sheets_area = QWidget()
        sheets_layout = QVBoxLayout(self.sheets_area)
        sheets_layout.setContentsMargins(0, 0, 0, 0)
        sheets_layout.setSpacing(6)
        sheets_layout.addWidget(section_label("选择文件"))
        sf_row = QHBoxLayout()
        self.sheet_file_btn = QPushButton("选择文件")
        self.sheet_file_btn.setStyleSheet(self._btn_style())
        self.sheet_file_btn.clicked.connect(self._select_file_for_sheets)
        sf_row.addWidget(self.sheet_file_btn)
        self.sheet_file_label = QLabel("未选择文件")
        self.sheet_file_label.setStyleSheet(f"color: {TEXT_MUTED};")
        sf_row.addWidget(self.sheet_file_label)
        sf_row.addStretch()
        sheets_layout.addLayout(sf_row)
        sheets_layout.addWidget(section_label("勾选要合并的 Sheet"))
        self.sheet_list = QListWidget()
        self.sheet_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sheet_list.setMaximumHeight(100)
        sheets_layout.addWidget(self.sheet_list)
        self.sheets_area.setVisible(False)
        layout.addWidget(self.sheets_area)

        # ── 输出 ──
        layout.addWidget(section_label("输出目录"))
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("选择输出目录")
        out_row.addWidget(self.output_dir_input)
        out_btn = QPushButton("浏览")
        out_btn.setFixedWidth(60)
        out_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        name_row = QHBoxLayout()
        name_row.addWidget(section_label("输出文件名"))
        self.output_name_input = QLineEdit("合并结果.xlsx")
        self.output_name_input.setFixedWidth(250)
        name_row.addWidget(self.output_name_input)
        name_row.addStretch()
        layout.addLayout(name_row)

        layout.addStretch()

        # ── 开始按钮 ──
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        self.start_btn = QPushButton("▶  开始合并")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; "
            f"border-radius: {RADIUS_SM}px; padding: 10px 40px; font-size: 12pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }} "
            f"QPushButton:disabled {{ background-color: {TEXT_MUTED}; }}"
        )
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
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt;")
        layout.addWidget(self.status_label)

        # ── 打开目录 ──
        open_row = QHBoxLayout()
        open_row.addStretch()
        self.open_dir_btn = QPushButton("\U0001F4C2 打开输出目录")
        self.open_dir_btn.setStyleSheet(
            f"QPushButton {{ background-color: {SUCCESS}; color: white; border: none; "
            f"border-radius: {RADIUS_SM}px; padding: 10px 28px; font-size: 11pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: #15803D; }}"
        )
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        open_row.addWidget(self.open_dir_btn)
        open_row.addStretch()
        layout.addLayout(open_row)

    @staticmethod
    def _btn_style() -> str:
        return (
            f"QPushButton {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; "
            f"border-radius: {RADIUS_SM}px; padding: 5px 14px; color: {TEXT_PRIMARY}; }} "
            f"QPushButton:hover {{ border-color: {PRIMARY}; color: {PRIMARY}; }}"
        )

    def _on_mode_changed(self):
        is_files = self.mode_files.isChecked()
        self.files_area.setVisible(is_files)
        self.sheets_area.setVisible(not is_files)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
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
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
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
                self.sheet_file_label.setText(f"读取失败：{e}")

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
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
                self.status_label.setText("请至少添加 2 个文件")
                return
            self._worker.configure(
                mode="files", file_paths=self._file_paths,
                output_dir=output_dir, output_name=output_name,
            )
        else:
            selected = [self.sheet_list.item(i).text() for i in range(self.sheet_list.count()) if self.sheet_list.item(i).isSelected()]
            if not selected or not self._file_path:
                self.status_label.setText("请选择文件和至少一个 Sheet")
                return
            self._worker.configure(
                mode="sheets", file_path=self._file_path,
                sheet_names=selected, output_dir=output_dir, output_name=output_name,
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
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, summary: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  开始合并")
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  开始合并")
        self.status_label.setText(f"❌ 合并失败：{error_msg}")
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            os.startfile(self._output_dir)
