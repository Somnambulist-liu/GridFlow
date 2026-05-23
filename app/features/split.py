"""拆分功能模块"""
import os
from app.platform_utils import open_file_explorer
from app.settings import get_default_output_dir, get_auto_open_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QRadioButton, QLineEdit,
    QTableView, QHeaderView, QProgressBar, QFrame,
    QToolButton, QStackedWidget, QMenu, QCheckBox,
)
from PySide6.QtCore import Signal, Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QDragEnterEvent, QDropEvent

from core.reader import get_sheet_names, get_columns, get_unique_values
from core.splitter import SplitWorker
from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.step_indicator import StepIndicator
from app.widgets.common import get_combo_style, setup_preset_menu


class SplitFeature(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: SplitWorker | None = None
        self._current_step = 0
        self._current_preview_data = {}
        self._theme = ThemeManager.instance()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang = LangManager.instance()
        self._lang.lang_changed.connect(self._on_lang_changed)
        self._setup_ui()
        self._connect_signals()
        self._apply_styles()
        self._apply_lang()

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
        self.footer = QWidget()
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        self.back_btn = QPushButton()
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_prev)
        footer_layout.addWidget(self.back_btn)

        footer_layout.addStretch()

        self.next_btn = QPushButton()
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._go_next)
        footer_layout.addWidget(self.next_btn)

        layout.addWidget(self.footer)

    def _nav_btn_style(self, primary: bool = False) -> str:
        c = self._theme.current_colors
        if primary:
            return (
                f"QPushButton {{ background-color: {c['PRIMARY']}; color: white; border: none; "
                f"border-radius: {c['RADIUS_SM']}px; padding: 8px 24px; font-size: 11pt; font-weight: bold; }} "
                f"QPushButton:hover {{ background-color: {c['PRIMARY_HOVER']}; }} "
                f"QPushButton:disabled {{ background-color: {c['TEXT_MUTED']}; }}"
            )
        return (
            f"QPushButton {{ background-color: transparent; color: {c['TEXT_SECONDARY']}; "
            f"border: 1px solid {c['BORDER']}; border-radius: {c['RADIUS_SM']}px; padding: 8px 20px; font-size: 11pt; }} "
            f"QPushButton:hover {{ color: #1E293B; border-color: {c['TEXT_MUTED']}; }}"
        )

    def _on_theme_changed(self, _theme_name: str):
        self._apply_styles()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def _apply_lang(self):
        """Update all user-visible text from current language."""
        self.back_btn.setText(self._lang.tr("split.step_back"))
        self.next_btn.setText(self._lang.tr("split.step_next"))

    def _apply_styles(self):
        c = self._theme.current_colors
        self.footer.setStyleSheet(f"background-color: {c['BG_CARD']}; border-top: 1px solid {c['BORDER']};")
        self.back_btn.setStyleSheet(self._nav_btn_style())
        self.next_btn.setStyleSheet(self._nav_btn_style(primary=True))
        self.step1._apply_styles()
        self.step2._apply_styles()
        self.step3._apply_styles()

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
            self.next_btn.setEnabled(bool(self.step1.file_path))
        elif step == 1:
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
            preserve_formulas=config["preserve_formulas"],
        )
        self._worker.progress.connect(self.step3.update_progress)
        self._worker.finished.connect(self._on_split_finished)
        self._worker.error_occurred.connect(self._on_split_error)
        self._worker.start()

    def _on_split_finished(self, summary: str):
        config = self.step2.get_config()
        self.step3.show_result_stats(config["output_dir"])
        self.step3.on_finished(summary)
        if get_auto_open_dir():
            self.step3._open_output_dir()

    def _on_split_error(self, error_msg: str):
        self.step3.on_error(error_msg)


# ── Step 1: 选择文件 ────────────────────────────────────────
class _Step1File(QWidget):
    file_selected = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._file_path = ""
        self._loaded_name = ""
        self._file_sheets_count = 0
        self._file_error_msg = ""
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._lang.lang_changed.connect(self._on_lang_changed)
        self._setup_ui()
        self._apply_lang()

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
        self._hero_title = QLabel()
        self._hero_title.setAlignment(Qt.AlignCenter)
        hero.addWidget(self._hero_title)
        self._hero_sub = QLabel()
        self._hero_sub.setAlignment(Qt.AlignCenter)
        hero.addWidget(self._hero_sub)
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
        self._dz_text = QLabel()
        self._dz_text.setAlignment(Qt.AlignCenter)
        dz_layout.addWidget(self._dz_text)
        layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        self.browse_btn = QPushButton()
        self.browse_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(self.browse_btn)
        layout.addLayout(btn_row)

        self.file_info = QLabel("")
        self.file_info.setAlignment(Qt.AlignCenter)
        self.file_info.setWordWrap(True)
        layout.addWidget(self.file_info)
        layout.addStretch()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def _apply_lang(self):
        """Update all user-visible text from current language."""
        self._hero_title.setText(self._lang.tr("split.hero_title"))
        self._hero_sub.setText(self._lang.tr("split.hero_sub"))
        self._dz_text.setText(self._lang.tr("split.drop_hint"))
        self.browse_btn.setText(self._lang.tr("split.browse_btn"))
        self._update_file_info_text()

    def _update_file_info_text(self):
        """Update file_info label based on stored state."""
        c = self._theme.current_colors
        if self._file_error_msg:
            self.file_info.setText(self._lang.tr("split.file_error", error=self._file_error_msg))
            self.file_info.setStyleSheet(f"color: {c['DANGER']}; font-size: 10pt;")
        elif self._loaded_name:
            self.file_info.setText(
                self._lang.tr("split.file_loaded", name=self._loaded_name, count=self._file_sheets_count)
            )
            self.file_info.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 11pt; font-weight: bold; margin-top: 8px;")
        else:
            self.file_info.setText("")

    def _apply_styles(self):
        c = self._theme.current_colors
        self._hero_title.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {c['TEXT_PRIMARY']};")
        self._hero_sub.setStyleSheet(f"font-size: 10pt; color: {c['TEXT_MUTED']};")
        self._dz_text.setStyleSheet(f"font-size: 10pt; color: {c['TEXT_MUTED']};")
        self.browse_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['PRIMARY']}; color: white; border: none; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 8px 24px; font-size: 11pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {c['PRIMARY_HOVER']}; }}"
        )

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._lang.tr("split.hero_title"), "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        try:
            sheets = get_sheet_names(file_path)
            self._file_path = file_path
            self._loaded_name = os.path.basename(file_path)
            self._file_sheets_count = len(sheets)
            self._file_error_msg = ""
            self._update_file_info_text()
            self.file_selected.emit(file_path, sheets)
        except Exception as e:
            self._file_error_msg = str(e)
            self._loaded_name = ""
            self._file_sheets_count = 0
            self._update_file_info_text()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith((".xlsx", ".xls")):
                event.acceptProposedAction()
                c = self._theme.current_colors
                self.drop_zone.setStyleSheet(
                    f"background-color: {c['PRIMARY_LIGHT']}; border: 2px dashed {c['PRIMARY']}; border-radius: {c['RADIUS_LG']}px;")
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


# ── Step 2: 拆分配置 ──────────────────────────────────────
class _Step2Config(QWidget):
    config_valid = Signal(bool)
    column_loaded = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = ""
        self._sheets = []
        self._current_values: dict = {}
        self._current_column = ""
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._lang.lang_changed.connect(self._on_lang_changed)
        self._prefix_presets = [
            ("", ""), ("2024年_", "2024年_"), ("数据_", "数据_"),
            ("报表_", "报表_"), ("分类_", "分类_"), ("导出_", "导出_"),
        ]
        self._suffix_presets = [
            ("", ""), ("_副本", "_副本"), ("_统计", "_统计"),
            ("_汇总", "_汇总"), ("_结果", "_结果"), ("_整理", "_整理"),
        ]
        self._setup_ui()
        self._apply_lang()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(14)

        row1 = QHBoxLayout()
        row1.setSpacing(20)
        g1 = QVBoxLayout()
        g1.setSpacing(4)
        self._sheet_section_label = QLabel()
        g1.addWidget(self._sheet_section_label)
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        g1.addWidget(self.sheet_combo)
        row1.addLayout(g1)
        g2 = QVBoxLayout()
        g2.setSpacing(4)
        self._column_section_label = QLabel()
        g2.addWidget(self._column_section_label)
        self.column_combo = QComboBox()
        self.column_combo.currentTextChanged.connect(self._on_column_changed)
        g2.addWidget(self.column_combo)
        row1.addLayout(g2)
        layout.addLayout(row1)

        self._mode_section_label = QLabel()
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

        self._output_section_label = QLabel()
        layout.addWidget(self._output_section_label)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        default_dir = get_default_output_dir()
        if default_dir:
            self.output_dir_input.setText(default_dir)
        out_row.addWidget(self.output_dir_input)
        self.out_btn = QPushButton()
        self.out_btn.setFixedWidth(60)
        self.out_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.out_btn)
        layout.addLayout(out_row)

        self.formula_check = QCheckBox()
        layout.addWidget(self.formula_check)

        self.naming_title = QLabel()
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
        self.prefix_input.setFixedWidth(90)
        self.prefix_input.textChanged.connect(self._update_naming_preview)
        prefix_group.addWidget(self.prefix_input)
        self._p_btn = QToolButton()
        self._p_btn.setText("▼")
        self._p_btn.setPopupMode(QToolButton.InstantPopup)
        self._p_btn.setFixedWidth(20)
        prefix_group.addWidget(self._p_btn)
        name_row.addLayout(prefix_group)
        self._plus1 = QLabel("+")
        name_row.addWidget(self._plus1)
        self.field_btn = QToolButton()
        self.field_btn.setPopupMode(QToolButton.InstantPopup)
        self.field_btn.setEnabled(False)
        name_row.addWidget(self.field_btn)
        self._plus2 = QLabel("+")
        name_row.addWidget(self._plus2)
        suffix_group = QHBoxLayout()
        suffix_group.setSpacing(1)
        self.suffix_input = QLineEdit()
        self.suffix_input.setFixedWidth(90)
        self.suffix_input.textChanged.connect(self._update_naming_preview)
        suffix_group.addWidget(self.suffix_input)
        self._s_btn = QToolButton()
        self._s_btn.setText("▼")
        self._s_btn.setPopupMode(QToolButton.InstantPopup)
        self._s_btn.setFixedWidth(20)
        suffix_group.addWidget(self._s_btn)
        name_row.addLayout(suffix_group)
        self._dot_label = QLabel(".xlsx")
        name_row.addWidget(self._dot_label)
        name_row.addStretch()
        naming_layout.addLayout(name_row)
        self.naming_preview = QLabel()
        naming_layout.addWidget(self.naming_preview)
        layout.addWidget(self.naming_container)
        layout.addStretch()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def _apply_lang(self):
        """Update all user-visible text from current language."""
        self._sheet_section_label.setText(self._lang.tr("split.select_sheet"))
        self.sheet_combo.setPlaceholderText(self._lang.tr("split.select_sheet_placeholder"))
        self._column_section_label.setText(self._lang.tr("split.split_column"))
        self.column_combo.setPlaceholderText(self._lang.tr("split.select_column_placeholder"))
        self._mode_section_label.setText(self._lang.tr("split.split_mode"))
        self.mode_files.setText(self._lang.tr("split.mode_files"))
        self.mode_sheets.setText(self._lang.tr("split.mode_sheets"))
        self._output_section_label.setText(self._lang.tr("split.output_dir"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("split.output_dir_placeholder"))
        self.out_btn.setText(self._lang.tr("label.browse"))
        self.formula_check.setText(self._lang.tr("split.preserve_formulas"))
        self.naming_title.setText(self._lang.tr("split.file_naming"))
        self.prefix_input.setPlaceholderText(self._lang.tr("split.prefix_placeholder"))
        self.suffix_input.setPlaceholderText(self._lang.tr("split.suffix_placeholder"))
        self.field_btn.setToolTip(self._lang.tr("split.field_tooltip"))
        # Update presets with translated "None"
        none_text = self._lang.tr("split.preset_none")
        self._prefix_presets[0] = (none_text, "")
        self._suffix_presets[0] = (none_text, "")
        # Rebuild dynamic texts
        self._update_naming_preview()
        if self._current_values:
            self._build_field_menu(self._current_values)
        else:
            self.field_btn.setText(f"{{{self._lang.tr('split.col_value')}}}")
        # If no values loaded yet, show the hint
        if not self._current_values:
            self.naming_preview.setText(self._lang.tr("split.naming_preview_hint"))
        # Rebuild preset menus
        c = self._theme.current_colors
        setup_preset_menu(self._p_btn, self.prefix_input, self._prefix_presets, c)
        setup_preset_menu(self._s_btn, self.suffix_input, self._suffix_presets, c)

    def _apply_styles(self):
        c = self._theme.current_colors
        self._sheet_section_label.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-bottom: 2px;")
        self._column_section_label.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-bottom: 2px;")
        self._mode_section_label.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-bottom: 2px;")
        self._output_section_label.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-bottom: 2px;")
        self.naming_title.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-bottom: 2px;")
        self.formula_check.setStyleSheet(
            f"QCheckBox {{ color: {c['TEXT_SECONDARY']}; font-size: 9pt; spacing: 6px; }} "
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid {c['BORDER']}; }} "
            f"QCheckBox::indicator:checked {{ border-color: {c['PRIMARY']}; background-color: {c['PRIMARY']}; }}"
        )
        self.sheet_combo.setStyleSheet(get_combo_style(c))
        self.column_combo.setStyleSheet(get_combo_style(c))
        self._plus1.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-weight: bold; font-size: 10pt;")
        self._plus2.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-weight: bold; font-size: 10pt;")
        self._dot_label.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-weight: bold; font-size: 10pt;")
        self.naming_preview.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 9pt;")
        self.field_btn.setStyleSheet(
            f"QToolButton {{ background-color: {c['PRIMARY_LIGHT']}; color: {c['PRIMARY']}; "
            f"padding: 4px 10px; border-radius: 4px; font-weight: bold; border: none; }} "
            f"QToolButton:hover {{ background-color: #BFDBFE; }} "
            "QToolButton::menu-indicator { image: none; }"
        )
        self._p_btn.setStyleSheet(
            f"QToolButton {{ color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: 0 4px 4px 0; background: {c['BG_INPUT']}; font-size: 7pt; }} "
            f"QToolButton:hover {{ background: {c['PRIMARY_LIGHT']}; }} "
            "QToolButton::menu-indicator { image: none; }"
        )
        self._s_btn.setStyleSheet(
            f"QToolButton {{ color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: 0 4px 4px 0; background: {c['BG_INPUT']}; font-size: 7pt; }} "
            f"QToolButton:hover {{ background: {c['PRIMARY_LIGHT']}; }} "
            "QToolButton::menu-indicator { image: none; }"
        )
        setup_preset_menu(self._p_btn, self.prefix_input, self._prefix_presets, c)
        setup_preset_menu(self._s_btn, self.suffix_input, self._suffix_presets, c)

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
        c = self._theme.current_colors
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: 6px; padding: 4px; }} "
            f"QMenu::item {{ padding: 5px 20px; border-radius: 3px; color: {c['TEXT_PRIMARY']}; }} "
            f"QMenu::item:selected {{ background-color: {c['PRIMARY_LIGHT']}; }}"
        )
        sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)
        max_count = max(values.values()) if values else 1
        for val, count in sorted_items:
            bar = "█" * int(count / max_count * 12)
            menu.addAction(
                self._lang.tr("split.field_item_fmt", val=val, count=count, bar=bar)
            ).setEnabled(False)
        if len(sorted_items) > 20:
            menu.addSeparator()
            menu.addAction(
                self._lang.tr("split.field_more_fmt", n=len(sorted_items))
            ).setEnabled(False)
        self.field_btn.setMenu(menu)
        cn = self._current_column or self._lang.tr("split.col_value")
        self.field_btn.setText(self._lang.tr("split.field_btn_fmt", cn=cn, n=len(values)))

    def _on_mode_changed(self):
        is_files = self.mode_files.isChecked()
        self.naming_container.setVisible(is_files)
        self.naming_title.setVisible(is_files)
        self._check_valid()

    def _update_naming_preview(self):
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        example = next(iter(self._current_values), self._lang.tr("split.col_value"))
        sample = f"{prefix}{example}{suffix}.xlsx"
        self.naming_preview.setText(self._lang.tr("split.naming_preview_fmt", sample=sample))

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, self._lang.tr("split.dialog_output_dir"))
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
            "preserve_formulas": self.formula_check.isChecked(),
        }


# ── Step 3: 预览执行 ──────────────────────────────────────
class _Step3Execute(QWidget):
    start_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_dir = ""
        self._mode = "files"
        self._column_name = ""
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._lang.lang_changed.connect(self._on_lang_changed)
        self._setup_ui()
        self._apply_lang()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(16)

        preview_header = QHBoxLayout()
        self._preview_label = QLabel()
        preview_header.addWidget(self._preview_label)
        self.summary_label = QLabel("")
        preview_header.addWidget(self.summary_label)
        preview_header.addStretch()
        self.search_input = QLineEdit()
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
        # Headers set by _apply_lang
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
        self._info_banner.setVisible(False)
        layout.addWidget(self._info_banner)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton()
        self.start_btn.setFixedHeight(44)
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
        bottom_layout.addWidget(self.status_label)
        open_row = QHBoxLayout()
        open_row.addStretch()
        self.open_dir_btn = QPushButton()
        self.open_dir_btn.setVisible(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        open_row.addWidget(self.open_dir_btn)
        open_row.addStretch()
        bottom_layout.addLayout(open_row)
        layout.addWidget(self.bottom_area)

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def _apply_lang(self):
        """Update all user-visible text from current language."""
        self._preview_label.setText(self._lang.tr("split.preview_title"))
        self.search_input.setPlaceholderText(self._lang.tr("split.search_placeholder"))
        self.model.setHorizontalHeaderLabels([
            self._lang.tr("split.col_value"),
            self._lang.tr("split.col_rows"),
            self._lang.tr("split.col_pct"),
        ])
        self.start_btn.setText(self._lang.tr("split.start_btn"))
        self.open_dir_btn.setText(self._lang.tr("common.open_output_dir"))
        # Rebuild info banner and summary with current data
        self._update_info_banner()
        self._refresh_summary()

    def _apply_styles(self):
        c = self._theme.current_colors
        self._preview_label.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {c['TEXT_PRIMARY']};")
        self.summary_label.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-size: 9pt;")
        self._info_banner.setStyleSheet(f"font-size: 11pt; color: {c['TEXT_PRIMARY']}; font-weight: bold;")
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

    def _on_start(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText(self._lang.tr("common.processing"))
        self._info_banner.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(self._lang.tr("split.reading_data"))
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
        self._refresh_summary()
        self.search_input.setVisible(vc > 10)
        if vc <= 10:
            self.search_input.clear()
        self._update_info_banner()

    def _refresh_summary(self):
        """Refresh the summary label text using current language."""
        vc = self.model.rowCount()
        if vc == 0:
            self.summary_label.setText("")
            return
        total_rows = 0
        for r in range(vc):
            total_rows += int(self.model.item(r, 1).text())
        self.summary_label.setText(self._lang.tr("split.summary_fmt", vc=vc, total_rows=total_rows))

    def _update_info_banner(self):
        if not self._column_name or self.model.rowCount() == 0:
            self._info_banner.setVisible(False)
            return
        vc = self.model.rowCount()
        total = 0
        for r in range(vc):
            total += int(self.model.item(r, 1).text())
        if self._mode == "files":
            self._info_banner.setText(
                self._lang.tr("split.info_banner_files", column=self._column_name, vc=vc, total=total)
            )
        else:
            self._info_banner.setText(
                self._lang.tr("split.info_banner_sheets", column=self._column_name, vc=vc, total=total)
            )
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
        self.start_btn.setText(self._lang.tr("split.done"))
        self.status_label.setText(summary)
        c = self._theme.current_colors
        self.status_label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def on_error(self, error_msg: str):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self._lang.tr("split.start_btn"))
        self.status_label.setText(self._lang.tr("split.error_fmt", error=error_msg))
        c = self._theme.current_colors
        self.status_label.setStyleSheet(f"color: {c['DANGER']}; font-size: 10pt; font-weight: bold;")
        self.progress_bar.setVisible(False)

    def show_result_stats(self, output_dir: str):
        self._output_dir = output_dir
        self.open_dir_btn.setVisible(True)

    def _open_output_dir(self):
        if self._output_dir and os.path.exists(self._output_dir):
            open_file_explorer(self._output_dir)
