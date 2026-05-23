"""拆分功能模块"""
import os
from app.platform_utils import open_file_explorer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QRadioButton, QLineEdit,
    QTableView, QHeaderView, QProgressBar, QFrame,
    QToolButton, QStackedWidget, QMenu,
)
from PySide6.QtCore import Signal, Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QDragEnterEvent, QDropEvent

from core.reader import get_sheet_names, get_columns, get_unique_values
from core.splitter import SplitWorker
from app.theme import (
    PRIMARY, PRIMARY_HOVER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, BG_CARD, BG_INPUT, BG_MAIN, PRIMARY_LIGHT,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)
from app.step_indicator import StepIndicator
from app.widgets.common import COMBO_STYLE, setup_preset_menu, section_label, make_drop_btn


class SplitFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: SplitWorker | None = None
        self._current_step = 0
        self._current_preview_data = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 步骤条
        self.step_indicator = StepIndicator()
        layout.addWidget(self.step_indicator)

        # 步骤内容
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: transparent;")
        self.step1 = _Step1File()
        self.step2 = _Step2Config()
        self.step3 = _Step3Execute()
        self.stack.addWidget(self.step1)
        self.stack.addWidget(self.step2)
        self.stack.addWidget(self.step3)
        layout.addWidget(self.stack, 1)

        # 底部导航
        footer = QWidget()
        footer.setStyleSheet(f"background-color: {BG_CARD}; border-top: 1px solid {BORDER};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        self.back_btn = QPushButton("←  上一步")
        self.back_btn.setStyleSheet(self._nav_btn_style())
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_prev)
        footer_layout.addWidget(self.back_btn)

        footer_layout.addStretch()

        self.next_btn = QPushButton("下一步  →")
        self.next_btn.setStyleSheet(self._nav_btn_style(primary=True))
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._go_next)
        footer_layout.addWidget(self.next_btn)

        layout.addWidget(footer)

    def _nav_btn_style(self, primary: bool = False) -> str:
        if primary:
            return (
                f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; "
                f"border-radius: {RADIUS_SM}px; padding: 8px 24px; font-size: 11pt; font-weight: bold; }} "
                f"QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }} "
                f"QPushButton:disabled {{ background-color: {TEXT_MUTED}; }}"
            )
        return (
            f"QPushButton {{ background-color: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px; padding: 8px 20px; font-size: 11pt; }} "
            f"QPushButton:hover {{ color: #1E293B; border-color: {TEXT_MUTED}; }}"
        )

    def _connect_signals(self):
        self.step1.file_selected.connect(self._on_file_loaded)
        self.step2.config_valid.connect(self._on_config_valid)
        self.step2.column_loaded.connect(self._on_preview_update)
        self.step3.start_requested.connect(self._start_split)

    def _go_next(self):
        if self._current_step == 0:
            self._navigate_to(1)
        elif self._current_step == 1:
            self._navigate_to(2)

    def _go_prev(self):
        if self._current_step > 0:
            self._navigate_to(self._current_step - 1)

    def _navigate_to(self, step: int):
        self._current_step = step
        self.stack.setCurrentIndex(step)
        self.step_indicator.set_current(step)
        self.back_btn.setVisible(step > 0)
        self.next_btn.setVisible(step < 2)
        if step == 0:
            self.next_btn.setText("下一步  →")
            self.next_btn.setEnabled(bool(self.step1.file_path))
        elif step == 1:
            self.next_btn.setText("下一步  →")
            self.next_btn.setEnabled(self.step2.is_valid())
        elif step == 2:
            self.next_btn.setVisible(False)
            mode = self.step2.get_config()["mode"]
            self.step3.set_mode(mode)

    def _on_file_loaded(self, file_path: str, sheets: list):
        self.next_btn.setEnabled(True)
        self.step2.load_file(file_path, sheets)

    def _on_config_valid(self, valid: bool):
        if self._current_step == 1:
            self.next_btn.setEnabled(valid)

    def _on_preview_update(self, column_name: str, value_counts: dict):
        self._current_preview_data = value_counts
        mode = self.step2.get_config()["mode"]
        self.step3.set_mode(mode)
        self.step3.update_preview(column_name, value_counts)
        self.step3.set_ready(True)

    def _start_split(self):
        config = self.step2.get_config()
        if not config["file_path"]:
            return
        if config["mode"] == "sheets":
            output_path = os.path.join(
                config["output_dir"],
                f"{os.path.splitext(os.path.basename(config['file_path']))[0]}_拆分结果.xlsx"
            )
        else:
            output_path = ""
        self._worker = SplitWorker(self)
        self._worker.configure(
            file_path=config["file_path"], sheet_name=config["sheet_name"],
            column=config["column"], mode=config["mode"],
            output_dir=config["output_dir"], output_path=output_path,
            name_pattern=config["name_pattern"], keep_header=config["keep_header"],
        )
        self._worker.progress.connect(self.step3.update_progress)
        self._worker.finished.connect(self._on_split_finished)
        self._worker.error_occurred.connect(self._on_split_error)
        self._worker.start()

    def _on_split_finished(self, summary: str):
        config = self.step2.get_config()
        self.step3.show_result_stats(config["output_dir"])
        self.step3.on_finished(summary)

    def _on_split_error(self, error_msg: str):
        self.step3.on_error(error_msg)


# ─── Step 1: 选择文件 ────────────────────────────────────────
class _Step1File(QWidget):
    file_selected = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._file_path = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        hero = QVBoxLayout()
        hero.setAlignment(Qt.AlignCenter)
        hero.setSpacing(8)
        icon_label = QLabel("\U0001F4E5")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        hero.addWidget(icon_label)
        hero_title = QLabel("选择要拆分的 Excel 文件")
        hero_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1E293B;")
        hero_title.setAlignment(Qt.AlignCenter)
        hero.addWidget(hero_title)
        hero_sub = QLabel("支持 .xlsx / .xls 格式，可拖拽文件到此处")
        hero_sub.setStyleSheet(f"font-size: 10pt; color: {TEXT_MUTED};")
        hero_sub.setAlignment(Qt.AlignCenter)
        hero.addWidget(hero_sub)
        layout.addLayout(hero)
        layout.addSpacing(20)

        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setFixedHeight(120)
        dz_layout = QVBoxLayout(self.drop_zone)
        dz_layout.setAlignment(Qt.AlignCenter)
        dz_layout.setSpacing(8)
        dz_icon = QLabel("\U0001F4C1")
        dz_icon.setStyleSheet("font-size: 36px;")
        dz_icon.setAlignment(Qt.AlignCenter)
        dz_layout.addWidget(dz_icon)
        dz_text = QLabel("拖拽 Excel 文件到此处")
        dz_text.setStyleSheet(f"font-size: 10pt; color: {TEXT_MUTED};")
        dz_text.setAlignment(Qt.AlignCenter)
        dz_layout.addWidget(dz_text)
        layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        self.browse_btn = QPushButton("浏览选择文件")
        self.browse_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; "
            f"border-radius: {RADIUS_SM}px; padding: 8px 24px; font-size: 11pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }}"
        )
        self.browse_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(self.browse_btn)
        layout.addLayout(btn_row)

        self.file_info = QLabel("")
        self.file_info.setAlignment(Qt.AlignCenter)
        self.file_info.setWordWrap(True)
        layout.addWidget(self.file_info)
        layout.addStretch()

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        try:
            sheets = get_sheet_names(file_path)
            self._file_path = file_path
            basename = os.path.basename(file_path)
            self.file_info.setText(f"✅ 已加载：{basename}（共 {len(sheets)} 个 Sheet）")
            self.file_info.setStyleSheet(f"color: {SUCCESS}; font-size: 11pt; font-weight: bold; margin-top: 8px;")
            self.file_selected.emit(file_path, sheets)
        except Exception as e:
            self.file_info.setText(f"❌ 无法读取文件：{e}")
            self.file_info.setStyleSheet("color: #DC2626; font-size: 10pt;")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith((".xlsx", ".xls")):
                event.acceptProposedAction()
                self.drop_zone.setStyleSheet(
                    f"background-color: {PRIMARY_LIGHT}; border: 2px dashed {PRIMARY}; border-radius: {RADIUS_LG}px;")
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_zone.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.drop_zone.setStyleSheet("")
        if event.mimeData().hasUrls():
            self._load_file(event.mimeData().urls()[0].toLocalFile())

    @property
    def file_path(self):
        return self._file_path


# ─── Step 2: 拆分配置 ──────────────────────────────────────
class _Step2Config(QWidget):
    config_valid = Signal(bool)
    column_loaded = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = ""
        self._sheets = []
        self._current_values: dict = {}
        self._current_column = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(14)

        row1 = QHBoxLayout()
        row1.setSpacing(20)
        g1 = QVBoxLayout()
        g1.setSpacing(4)
        g1.addWidget(section_label("选择 Sheet"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.setPlaceholderText("请先选择文件")
        self.sheet_combo.setStyleSheet(COMBO_STYLE)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        g1.addWidget(self.sheet_combo)
        row1.addLayout(g1)
        g2 = QVBoxLayout()
        g2.setSpacing(4)
        g2.addWidget(section_label("拆分字段"))
        self.column_combo = QComboBox()
        self.column_combo.setPlaceholderText("请先选择 Sheet")
        self.column_combo.setStyleSheet(COMBO_STYLE)
        self.column_combo.currentTextChanged.connect(self._on_column_changed)
        g2.addWidget(self.column_combo)
        row1.addLayout(g2)
        layout.addLayout(row1)

        layout.addWidget(section_label("拆分模式"))
        mode_row = QHBoxLayout()
        self.mode_files = QRadioButton("拆分为独立文件")
        self.mode_sheets = QRadioButton("拆分为多个 Sheet")
        self.mode_files.setChecked(True)
        self.mode_files.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_files)
        mode_row.addWidget(self.mode_sheets)
        mode_row.addStretch()
        layout.addLayout(mode_row)

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

        self.naming_title = section_label("文件命名")
        layout.addWidget(self.naming_title)
        self.naming_container = QWidget()
        naming_layout = QVBoxLayout(self.naming_container)
        naming_layout.setContentsMargins(0, 0, 0, 0)
        naming_layout.setSpacing(6)
        name_row = QHBoxLayout()
        name_row.setSpacing(4)
        prefix_group = QHBoxLayout()
        prefix_group.setSpacing(1)
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("前缀")
        self.prefix_input.setFixedWidth(90)
        self.prefix_input.textChanged.connect(self._update_naming_preview)
        prefix_group.addWidget(self.prefix_input)
        p_btn = make_drop_btn()
        setup_preset_menu(p_btn, self.prefix_input, [
            ("无", ""), ("日期_", "2024年_"), ("数据_", "数据_"),
            ("报表_", "报表_"), ("分类_", "分类_"), ("导出_", "导出_"),
        ])
        prefix_group.addWidget(p_btn)
        name_row.addLayout(prefix_group)
        plus1 = QLabel("+")
        plus1.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold; font-size: 10pt;")
        name_row.addWidget(plus1)
        self.field_btn = QToolButton()
        self.field_btn.setText("{字段值}")
        self.field_btn.setPopupMode(QToolButton.InstantPopup)
        self.field_btn.setToolTip("点击查看该字段的所有值")
        self.field_btn.setStyleSheet(
            f"QToolButton {{ background-color: {PRIMARY_LIGHT}; color: {PRIMARY}; "
            f"padding: 4px 10px; border-radius: 4px; font-weight: bold; border: none; }} "
            f"QToolButton:hover {{ background-color: #BFDBFE; }} "
            "QToolButton::menu-indicator { image: none; }"
        )
        self.field_btn.setEnabled(False)
        name_row.addWidget(self.field_btn)
        plus2 = QLabel("+")
        plus2.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold; font-size: 10pt;")
        name_row.addWidget(plus2)
        suffix_group = QHBoxLayout()
        suffix_group.setSpacing(1)
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("后缀")
        self.suffix_input.setFixedWidth(90)
        self.suffix_input.textChanged.connect(self._update_naming_preview)
        suffix_group.addWidget(self.suffix_input)
        s_btn = make_drop_btn()
        setup_preset_menu(s_btn, self.suffix_input, [
            ("无", ""), ("_副本", "_副本"), ("_统计", "_统计"),
            ("_汇总", "_汇总"), ("_结果", "_结果"), ("_整理", "_整理"),
        ])
        suffix_group.addWidget(s_btn)
        name_row.addLayout(suffix_group)
        dot_label = QLabel(".xlsx")
        dot_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 10pt;")
        name_row.addWidget(dot_label)
        name_row.addStretch()
        naming_layout.addLayout(name_row)
        self.naming_preview = QLabel("预览：选择字段后将显示示例")
        self.naming_preview.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 9pt;")
        naming_layout.addWidget(self.naming_preview)
        layout.addWidget(self.naming_container)
        layout.addStretch()

    def load_file(self, file_path: str, sheets: list):
        self._file_path = file_path
        self._sheets = sheets
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(sheets)
        self.sheet_combo.blockSignals(False)
        if sheets:
            self.sheet_combo.setCurrentIndex(0)
            self._on_sheet_changed(sheets[0])

    def _on_sheet_changed(self, sheet_name: str):
        if not sheet_name or not self._file_path:
            return
        try:
            cols = get_columns(self._file_path, sheet_name)
            self.column_combo.blockSignals(True)
            self.column_combo.clear()
            self.column_combo.addItems(cols)
            self.column_combo.blockSignals(False)
            if cols:
                self.column_combo.setCurrentIndex(0)
                self._on_column_changed(cols[0])
        except Exception:
            pass

    def _on_column_changed(self, column_name: str):
        if not column_name or not self._file_path:
            return
        try:
            sheet = self.sheet_combo.currentText()
            if not sheet:
                return
            values = get_unique_values(self._file_path, sheet, column_name)
            self._current_values = values
            self._current_column = column_name
            self._build_field_menu(values)
            self.field_btn.setEnabled(True)
            self._update_naming_preview()
            self.column_loaded.emit(column_name, values)
        except Exception:
            pass

    def _build_field_menu(self, values: dict):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: white; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px; } "
            "QMenu::item { padding: 5px 20px; border-radius: 3px; } "
            "QMenu::item:selected { background-color: #DBEAFE; }"
        )
        sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)
        max_count = max(values.values()) if values else 1
        for val, count in sorted_items:
            bar = "█" * int(count / max_count * 12)
            menu.addAction(f"{val}  ({count} 行)  {bar}").setEnabled(False)
        if len(sorted_items) > 20:
            menu.addSeparator()
            menu.addAction(f"... 共 {len(sorted_items)} 个值").setEnabled(False)
        self.field_btn.setMenu(menu)
        cn = self._current_column or "字段值"
        self.field_btn.setText(f"{{{cn}}}  ({len(values)}个)")

    def _on_mode_changed(self):
        is_files = self.mode_files.isChecked()
        self.naming_container.setVisible(is_files)
        self.naming_title.setVisible(is_files)
        self._check_valid()

    def _update_naming_preview(self):
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        example = next(iter(self._current_values), "字段值")
        sample = f"{prefix}{example}{suffix}.xlsx"
        self.naming_preview.setText(f"预览：{sample}")

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _check_valid(self):
        valid = bool(self._file_path and self.sheet_combo.currentText() and self.column_combo.currentText())
        self.config_valid.emit(valid)

    def is_valid(self) -> bool:
        return bool(self._file_path and self.sheet_combo.currentText() and self.column_combo.currentText())

    def get_config(self) -> dict:
        sheet = self.sheet_combo.currentText()
        column = self.column_combo.currentText()
        mode = "files" if self.mode_files.isChecked() else "sheets"
        output_dir = self.output_dir_input.text().strip() or os.path.dirname(self._file_path)
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        name_pattern = f"{prefix}{{value}}{suffix}.xlsx"
        return {
            "file_path": self._file_path, "sheet_name": sheet,
            "column": column, "mode": mode,
            "output_dir": output_dir, "name_pattern": name_pattern,
            "keep_header": True,
        }


# ─── Step 3: 预览执行 ──────────────────────────────────────
class _Step3Execute(QWidget):
    start_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_dir = ""
        self._mode = "files"
        self._column_name = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(16)

        preview_header = QHBoxLayout()
        preview_label = QLabel("\U0001F50D  数据预览")
        preview_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #1E293B;")
        preview_header.addWidget(preview_label)
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9pt;")
        preview_header.addWidget(self.summary_label)
        preview_header.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索过滤...")
        self.search_input.setFixedWidth(180)
        self.search_input.setVisible(False)
        self.search_input.textChanged.connect(self._apply_filter)
        preview_header.addWidget(self.search_input)
        layout.addLayout(preview_header)

        self.table_view = QTableView()
        self.table_view.setStyleSheet(
            "QTableView { border: none; background-color: transparent; }"
            "QTableView::item { padding: 4px 8px; }"
        )
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(False)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setMinimumHeight(120)
        self.model = QStandardItemModel()
        self.model.setColumnCount(3)
        self.model.setHorizontalHeaderLabels(["字段值", "行数", "占比"])
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)
        self.table_view.setModel(self.proxy_model)
        hdr = self.table_view.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table_view.setColumnWidth(1, 80)
        self.table_view.setColumnWidth(2, 80)
        layout.addWidget(self.table_view, 1)

        self._info_banner = QLabel("")
        self._info_banner.setAlignment(Qt.AlignCenter)
        self._info_banner.setWordWrap(True)
        self._info_banner.setStyleSheet(f"font-size: 11pt; color: {TEXT_PRIMARY}; font-weight: bold;")
        self._info_banner.setVisible(False)
        layout.addWidget(self._info_banner)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton("▶  开始拆分")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; "
            f"border-radius: {RADIUS_SM}px; padding: 10px 40px; font-size: 12pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }} "
            f"QPushButton:disabled {{ background-color: {TEXT_MUTED}; }}"
        )
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self.start_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addSpacing(8)

        self.bottom_area = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_area)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt;")
        bottom_layout.addWidget(self.status_label)
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
        bottom_layout.addLayout(open_row)
        layout.addWidget(self.bottom_area)

    def _on_start(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText("处理中...")
        self._info_banner.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在读取数据...")
        self.open_dir_btn.setVisible(False)
        self.start_requested.emit()

    def set_mode(self, mode: str):
        self._mode = mode
        self._update_info_banner()

    def update_preview(self, column_name: str, value_counts: dict):
        self.model.removeRows(0, self.model.rowCount())
        self._column_name = column_name
        if not value_counts:
            self.summary_label.setText("")
            self._info_banner.setVisible(False)
            return
        total_rows = sum(value_counts.values())
        rows = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
        for value, count in rows:
            pct = f"{count / total_rows * 100:.1f}%"
            self.model.appendRow([QStandardItem(str(value)), QStandardItem(str(count)), QStandardItem(pct)])
        vc = len(rows)
        self.summary_label.setText(f"共 {vc} 个不同值，{total_rows} 行数据")
        self.search_input.setVisible(vc > 10)
        if vc <= 10:
            self.search_input.clear()
        self._update_info_banner()

    def _update_info_banner(self):
        if not self._column_name or self.model.rowCount() == 0:
            self._info_banner.setVisible(False)
            return
        vc = self.model.rowCount()
        total = 0
        for r in range(vc):
            total += int(self.model.item(r, 1).text())
        unit = "文件" if self._mode == "files" else "Sheet"
        self._info_banner.setText(f"将按「{self._column_name}」拆分为 {vc} 个{unit}，共 {total} 行数据")
        self._info_banner.setVisible(True)

    def _apply_filter(self, text: str):
        self.proxy_model.setFilterFixedString(text)

    def set_ready(self, ready: bool):
        self.start_btn.setEnabled(ready)

    def update_progress(self, current: int, total: int, message: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def on_finished(self, summary: str):
        self.start_btn.setEnabled(False)
        self.start_btn.setText("✓ 拆分完成")
        self.status_label.setText(summary)
        self.status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  开始拆分")
        self.status_label.setText(f"❌ 拆分失败：{error_msg}")
        self.status_label.setStyleSheet("color: #DC2626; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def show_result_stats(self, output_dir: str):
        self._output_dir = output_dir
        self.open_dir_btn.setVisible(True)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
