"""Settings dialog — 输出 / 更新 两张卡片，整体随主题。"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QRadioButton, QPushButton, QButtonGroup, QFrame,
    QLineEdit, QCheckBox, QFileDialog,
)
from PySide6.QtCore import Qt, Signal

from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.settings import (
    get_default_output_dir, set_default_output_dir,
    get_auto_open_dir, set_auto_open_dir,
    get_auto_check_update, set_auto_check_update,
    get_ignored_version, clear_ignored_version,
)
from app.updater import is_frozen


class SettingsDialog(QDialog):
    check_updates_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()

        self.setWindowTitle(self._lang.tr("settings.title"))
        self.setMinimumWidth(480)
        self.setModal(True)

        self._setup_ui()
        self._load_values()
        self._apply_lang()
        self._apply_styles()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    def _load_values(self):
        """把当前设置填进控件。"""
        self.output_dir_input.setText(get_default_output_dir())
        self.auto_open_check.setChecked(get_auto_open_dir())
        self.auto_check_update.setChecked(get_auto_check_update())

    # ── 构建 ────────────────────────────────────────────

    def _make_card(self, title_label: QLabel) -> tuple:
        """返回 (卡片, 卡片内容布局)：卡片用 BG_MAIN 底 + 圆角，把设置分组。"""
        card = QFrame()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 14)
        card_layout.setSpacing(10)
        title_label.setParent(card)
        card_layout.addWidget(title_label)
        return card, card_layout

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(14)

        # ── 语言（独立小卡片，两种语言本身就是这一组的全部内容）──
        self.lang_section = QLabel()
        lang_card, lang_layout = self._make_card(self.lang_section)

        self.lang_zh = QRadioButton()
        self.lang_en = QRadioButton()
        self.lang_group = QButtonGroup(self)
        self.lang_group.addButton(self.lang_zh, 0)
        self.lang_group.addButton(self.lang_en, 1)
        (self.lang_zh if self._lang.lang == "zh" else self.lang_en).setChecked(True)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(28)
        lang_row.addWidget(self.lang_zh)
        lang_row.addWidget(self.lang_en)
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)
        layout.addWidget(lang_card)

        # ── 输出 ──
        self.output_section = QLabel()
        out_card, out_layout = self._make_card(self.output_section)

        self.output_dir_label = QLabel()          # 以前只有 placeholder，没有常驻标签
        out_layout.addWidget(self.output_dir_label)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self.output_dir_input = QLineEdit()
        dir_row.addWidget(self.output_dir_input, 1)
        self.browse_btn = QPushButton()
        self.browse_btn.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(self.browse_btn)
        out_layout.addLayout(dir_row)

        self.auto_open_check = QCheckBox()
        out_layout.addWidget(self.auto_open_check)
        layout.addWidget(out_card)

        # ── 更新 ──
        self.update_section = QLabel()
        upd_card, upd_layout = self._make_card(self.update_section)

        self.auto_check_update = QCheckBox()
        upd_layout.addWidget(self.auto_check_update)

        check_row = QHBoxLayout()
        check_row.setSpacing(10)
        self.check_update_btn = QPushButton()
        self.check_update_btn.clicked.connect(self._on_check_updates)
        check_row.addWidget(self.check_update_btn)
        self._check_status = QLabel("")
        check_row.addWidget(self._check_status, 1)
        upd_layout.addLayout(check_row)

        self._frozen_hint = QLabel()
        self._frozen_hint.setWordWrap(True)
        upd_layout.addWidget(self._frozen_hint)

        self.ignored_row = QWidget()
        ignored_layout = QHBoxLayout(self.ignored_row)
        ignored_layout.setContentsMargins(0, 0, 0, 0)
        ignored_layout.setSpacing(8)
        self.ignored_label = QLabel()
        ignored_layout.addWidget(self.ignored_label)
        self.ignored_clear_btn = QPushButton()
        self.ignored_clear_btn.clicked.connect(self._on_clear_ignored)
        ignored_layout.addWidget(self.ignored_clear_btn)
        ignored_layout.addStretch()
        upd_layout.addWidget(self.ignored_row)
        layout.addWidget(upd_card)

        layout.addStretch()

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        self._section_labels = [self.lang_section, self.output_section, self.update_section]

    # ── 文案与样式 ──────────────────────────────────────

    def _apply_lang(self):
        lang = self._lang
        self.setWindowTitle(lang.tr("settings.title"))
        self.lang_section.setText(lang.tr("settings.language"))
        self.lang_zh.setText(lang.tr("settings.language.zh"))
        self.lang_en.setText(lang.tr("settings.language.en"))
        self.output_section.setText(lang.tr("settings.output_section"))
        self.output_dir_label.setText(lang.tr("settings.output_dir"))
        self.output_dir_input.setPlaceholderText(lang.tr("settings.output_dir_placeholder"))
        self.browse_btn.setText(lang.tr("label.browse"))
        self.auto_open_check.setText(lang.tr("settings.auto_open_dir"))
        self.update_section.setText(lang.tr("settings.update_section"))
        self.auto_check_update.setText(lang.tr("update.auto_check"))
        self.check_update_btn.setText(lang.tr("update.check_now"))
        self._frozen_hint.setText("" if is_frozen() else lang.tr("update.frozen_required"))
        self._frozen_hint.setVisible(not is_frozen())
        self.cancel_btn.setText(lang.tr("btn.cancel"))
        self.save_btn.setText(lang.tr("btn.save"))
        self._refresh_ignored()

    def _refresh_ignored(self):
        """显示当前已忽略的版本，并提供“恢复提示”入口。"""
        ignored = get_ignored_version()
        self.ignored_row.setVisible(bool(ignored))
        if ignored:
            self.ignored_label.setText(self._lang.tr("settings.ignored_version", version=ignored))
            self.ignored_clear_btn.setText(self._lang.tr("settings.ignored_clear"))

    def _apply_styles(self):
        c = self._theme.current_colors

        for lbl in self._section_labels:
            lbl.setStyleSheet(f"font-size: 10.5pt; font-weight: bold; color: {c['PRIMARY']};")
        self._check_status.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 9pt;")
        self._frozen_hint.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 9pt;")
        self.ignored_label.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-size: 9pt;")
        self.output_dir_label.setStyleSheet(f"color: {c['TEXT_PRIMARY']}; font-size: 10pt;")

        self.browse_btn.setStyleSheet(
            f"QPushButton {{ color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 6px 12px; font-size: 10pt; background: transparent; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }} "
            f"QPushButton:pressed {{ background-color: {c['PRIMARY_LIGHT']}; }} "
            f"QPushButton:focus {{ border: 2px solid {c['PRIMARY']}; }}"
        )
        self.check_update_btn.setStyleSheet(self.browse_btn.styleSheet())
        self.ignored_clear_btn.setStyleSheet(
            f"QPushButton {{ color: {c['PRIMARY']}; border: none; background: transparent; "
            f"padding: 2px 4px; font-size: 9pt; text-decoration: underline; }} "
            f"QPushButton:hover {{ color: {c['PRIMARY_HOVER']}; }}"
        )

        self.cancel_btn.setStyleSheet(
            f"QPushButton {{ padding: 6px 20px; border-radius: {c['RADIUS_SM']}px; font-size: 10pt; "
            f"color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; background: transparent; }} "
            f"QPushButton:hover {{ border-color: {c['TEXT_PRIMARY']}; color: {c['TEXT_PRIMARY']}; }} "
            f"QPushButton:pressed {{ background-color: {c['BG_MAIN']}; }} "
            f"QPushButton:focus {{ border: 2px solid {c['PRIMARY']}; }}"
        )
        self.save_btn.setStyleSheet(
            f"QPushButton {{ padding: 6px 20px; border-radius: {c['RADIUS_SM']}px; font-size: 10pt; "
            f"color: white; background-color: {c['PRIMARY']}; border: none; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {c['PRIMARY_HOVER']}; }} "
            f"QPushButton:pressed {{ background-color: {c['PRIMARY_ACTIVE']}; }} "
            f"QPushButton:focus {{ border: 2px solid {c['PRIMARY_HOVER']}; }}"
        )

    # ── 行为 ────────────────────────────────────────────

    def _browse_output_dir(self):
        start = self.output_dir_input.text() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, self._lang.tr("label.select_dir"), start)
        if path:
            self.output_dir_input.setText(path)

    def _on_save(self):
        new_lang = "zh" if self.lang_zh.isChecked() else "en"
        self._lang.set_lang(new_lang)

        set_default_output_dir(self.output_dir_input.text().strip())
        set_auto_open_dir(self.auto_open_check.isChecked())
        set_auto_check_update(self.auto_check_update.isChecked())
        self.accept()

    def _on_check_updates(self):
        self._check_status.setText(self._lang.tr("update.checking"))
        self.check_update_btn.setEnabled(False)
        self.check_updates_requested.emit()

    def set_check_status(self, text: str):
        """由主窗口回填检查结果。"""
        self._check_status.setText(text)
        self.check_update_btn.setEnabled(True)

    def _on_clear_ignored(self):
        clear_ignored_version()
        self._refresh_ignored()
        self._check_status.setText(self._lang.tr("settings.ignored_cleared"))

    def _on_theme_changed(self, _name):
        self._apply_styles()

    def _on_lang_changed(self, _lang):
        self._apply_lang()
