"""去重功能模块"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QRadioButton, QLineEdit,
    QListWidget, QAbstractItemView, QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names, get_columns
from core.deduper import DedupWorker
from app.theme import (
    PRIMARY, PRIMARY_HOVER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, BG_CARD, RADIUS_SM,
)
from app.widgets.common import COMBO_STYLE, section_label


class DedupFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: DedupWorker | None = None
        self._file_path = ""
        self._output_dir = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # ── 选择文件 ──
        layout.addWidget(section_label("选择文件"))
        file_row = QHBoxLayout()
        self.file_btn = QPushButton("选择文件")
        self.file_btn.setStyleSheet(self._btn_style())
        self.file_btn.clicked.connect(self._select_file)
        file_row.addWidget(self.file_btn)
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet(f"color: {TEXT_MUTED};")
        file_row.addWidget(self.file_label)
        file_row.addStretch()
        layout.addLayout(file_row)

        # ── Sheet + 列 ──
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        g1 = QVBoxLayout()
        g1.setSpacing(4)
        g1.addWidget(section_label("选择 Sheet"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.setStyleSheet(COMBO_STYLE)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        g1.addWidget(self.sheet_combo)
        row1.addLayout(g1)
        layout.addLayout(row1)

        layout.addWidget(section_label("去重依据列（可多选）"))
        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.column_list.setMaximumHeight(100)
        self.column_list.setStyleSheet(f"QListWidget {{ border: 1px solid {BORDER}; border-radius: 4px; }}")
        layout.addWidget(self.column_list)

        # ── 保留选项 ──
        layout.addWidget(section_label("重复行保留"))
        keep_row = QHBoxLayout()
        self.keep_first = QRadioButton("保留首次出现")
        self.keep_last = QRadioButton("保留最后出现")
        self.keep_first.setChecked(True)
        keep_row.addWidget(self.keep_first)
        keep_row.addWidget(self.keep_last)
        keep_row.addStretch()
        layout.addLayout(keep_row)

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
        self.start_btn = QPushButton("▶  开始去重")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; "
            f"border-radius: {RADIUS_SM}px; padding: 10px 40px; font-size: 12pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }} "
            f"QPushButton:disabled {{ background-color: {TEXT_MUTED}; }}"
        )
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
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt;")
        layout.addWidget(self.status_label)

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

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
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
            self.column_list.clear()
            self.column_list.addItems(cols)
            for i in range(self.column_list.count()):
                self.column_list.item(i).setSelected(True)
        except Exception:
            pass

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_dedup(self):
        sheet = self.sheet_combo.currentText()
        if not self._file_path or not sheet:
            self.status_label.setText("请选择文件和 Sheet")
            return
        columns = [self.column_list.item(i).text() for i in range(self.column_list.count()) if self.column_list.item(i).isSelected()]
        if not columns:
            self.status_label.setText("请选择至少一个去重列")
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
        self.start_btn.setText("▶  开始去重")
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  开始去重")
        self.status_label.setText(f"❌ 去重失败：{error_msg}")
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            os.startfile(self._output_dir)
