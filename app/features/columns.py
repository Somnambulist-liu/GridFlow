"""列操作功能模块"""
import os
from app.platform_utils import open_file_explorer
from app.settings import get_default_output_dir, get_auto_open_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QLineEdit, QListWidget, QAbstractItemView,
    QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from core.reader import get_sheet_names, get_columns
from core.column_ops import ColumnOpsWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.widgets.common import get_combo_style, section_label


class ColumnsFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ColumnOpsWorker | None = None
        self._file_path = ""
        self._output_dir = ""
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._renames = {}
        self._calc_columns = []
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
        self.sec_col_ops.setText(self._lang.tr("columns.column_ops"))
        self.sec_rename.setText(self._lang.tr("columns.rename_col"))
        self.rename_input.setPlaceholderText(self._lang.tr("columns.rename_placeholder"))
        self.rename_btn.setText(self._lang.tr("columns.rename_btn"))
        self.sec_calc.setText(self._lang.tr("columns.calc_col"))
        self.calc_name_input.setPlaceholderText(self._lang.tr("columns.calc_name_placeholder"))
        self.calc_expr_input.setPlaceholderText(self._lang.tr("columns.calc_expr_placeholder"))
        self.add_calc_btn.setText(self._lang.tr("columns.add_btn"))
        self.sec_output.setText(self._lang.tr("label.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("label.default_out_dir"))
        self.out_btn.setText(self._lang.tr("label.browse"))
        self.start_btn.setText(self._lang.tr("columns.start"))
        self.open_dir_btn.setText(self._lang.tr("common.open_output_dir"))
        self._update_calc_preview()

    def _apply_styles(self):
        c = self._theme.current_colors
        self.file_label.setStyleSheet(f"color: {c['TEXT_MUTED']};")
        self.file_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }}"
        )
        self.sheet_combo.setStyleSheet(get_combo_style(c))
        self.column_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {c['BORDER']}; border-radius: 4px; "
            f"color: {c['TEXT_PRIMARY']}; background-color: {c['BG_CARD']}; }}"
        )
        self.rename_col_combo.setStyleSheet(get_combo_style(c))
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
        self.add_calc_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; background-color: {c['PRIMARY_LIGHT']}; }}"
        )
        self.rename_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 5px 14px; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }}"
        )

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

        # ── 列操作 ──
        self.sec_col_ops = section_label("列操作（勾选保留，拖拽排序）")
        layout.addWidget(self.sec_col_ops)
        self.column_list = QListWidget()
        self.column_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.column_list.setMaximumHeight(140)
        self.column_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.column_list.itemChanged.connect(self._on_column_check)
        layout.addWidget(self.column_list)

        # ── 重命名 ──
        rename_row = QHBoxLayout()
        rename_row.setSpacing(8)
        self.sec_rename = section_label("重命名列")
        rename_row.addWidget(self.sec_rename)
        self.rename_col_combo = QComboBox()
        self.rename_col_combo.setFixedWidth(150)
        rename_row.addWidget(self.rename_col_combo)
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText("新列名")
        self.rename_input.setFixedWidth(180)
        rename_row.addWidget(self.rename_input)
        self.rename_btn = QPushButton("应用")
        self.rename_btn.clicked.connect(self._apply_rename)
        rename_row.addWidget(self.rename_btn)
        rename_row.addStretch()
        layout.addLayout(rename_row)

        # ── 计算列 ──
        calc_row = QHBoxLayout()
        calc_row.setSpacing(8)
        self.sec_calc = section_label("计算列")
        calc_row.addWidget(self.sec_calc)
        self.calc_name_input = QLineEdit()
        self.calc_name_input.setPlaceholderText("列名")
        self.calc_name_input.setFixedWidth(120)
        calc_row.addWidget(self.calc_name_input)
        self.calc_expr_input = QLineEdit()
        self.calc_expr_input.setPlaceholderText("公式，如 {单价} * {数量}")
        self.calc_expr_input.setFixedWidth(250)
        calc_row.addWidget(self.calc_expr_input)
        self.add_calc_btn = QPushButton("添加")
        self.add_calc_btn.clicked.connect(self._add_calc_column)
        calc_row.addWidget(self.add_calc_btn)
        calc_row.addStretch()
        layout.addLayout(calc_row)

        # ── 计算列预览 ──
        self.calc_preview = QLabel("")
        self.calc_preview.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.calc_preview)

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
        self.start_btn = QPushButton("▶  开始执行")
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._start_ops)
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
            self._renames.clear()
            self._calc_columns.clear()
            self.column_list.blockSignals(True)
            self.column_list.clear()
            self.rename_col_combo.blockSignals(True)
            self.rename_col_combo.clear()
            for col in cols:
                item = self.column_list.addItem(col)
                item.setCheckState(Qt.Checked)
                self.rename_col_combo.addItem(col)
            self.rename_col_combo.blockSignals(False)
            self.column_list.blockSignals(False)
            self._update_calc_preview()
        except Exception:
            pass

    def _on_column_check(self, item):
        self._update_calc_preview()

    def _apply_rename(self):
        old = self.rename_col_combo.currentText()
        new = self.rename_input.text().strip()
        if old and new:
            self._renames[old] = new
            self.rename_input.clear()
            self.status_label.setText(self._lang.tr("columns.rename_recorded", old=old, new=new))

    def _add_calc_column(self):
        name = self.calc_name_input.text().strip()
        expr = self.calc_expr_input.text().strip()
        if name and expr:
            self._calc_columns.append({"name": name, "expression": expr})
            self.calc_name_input.clear()
            self.calc_expr_input.clear()
            self._update_calc_preview()

    def _update_calc_preview(self):
        if not self._calc_columns:
            self.calc_preview.setText("")
        else:
            items = [f"{c['name']} = {c['expression']}" for c in self._calc_columns]
            self.calc_preview.setText(self._lang.tr("columns.calc_preview") + " | ".join(items))

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("label.dir_dialog"))
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_ops(self):
        sheet = self.sheet_combo.currentText()
        if not self._file_path or not sheet:
            self.status_label.setText(self._lang.tr("label.select_file_and_sheet"))
            return

        kept = []
        order = []
        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            if item.checkState() == Qt.Checked:
                kept.append(item.text())
            order.append(item.text())

        if not kept:
            self.status_label.setText(self._lang.tr("columns.keep_one"))
            return

        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_path)
        self._output_dir = output_dir
        base = os.path.splitext(os.path.basename(self._file_path))[0]
        output_name = f"{base}_列操作结果.xlsx"

        self._worker = ColumnOpsWorker(self)
        self._worker.configure(
            file_path=self._file_path, sheet_name=sheet,
            kept_columns=kept, renames=self._renames, order=order,
            calc_columns=self._calc_columns,
            output_dir=output_dir, output_name=output_name,
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
        self.start_btn.setText(self._lang.tr("columns.start"))
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)
        self.open_dir_btn.setVisible(True)
        if get_auto_open_dir():
            self._open_output_dir()

    def _on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("columns.start"))
        self.status_label.setText(self._lang.tr("columns.error_failed", error=error_msg))
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
