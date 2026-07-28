"""Settings dialog — language, default output dir, auto-open."""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QRadioButton, QPushButton, QButtonGroup, QFrame,
    QLineEdit, QCheckBox, QFileDialog,
)
from PySide6.QtCore import Qt

from PySide6.QtCore import Signal

from app.theme_manager import ThemeManager
from app.i18n import LangManager
from app.settings import get_default_output_dir, set_default_output_dir
from app.settings import get_auto_open_dir, set_auto_open_dir
from app.settings import get_auto_check_update, set_auto_check_update
from app.updater import is_frozen


class SettingsDialog(QDialog):
    check_updates_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()

        self.setWindowTitle(self._lang.tr("settings.title"))
        self.setMinimumWidth(420)
        self.setModal(True)

        self._setup_ui()
        self._apply_styles()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        self.title_label = QLabel(self._lang.tr("settings.title"))
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self.title_label)

        # ── Language section ──
        self.lang_section = QLabel(self._lang.tr("settings.language"))
        layout.addWidget(self.lang_section)

        self.lang_zh = QRadioButton(self._lang.tr("settings.language.zh"))
        self.lang_en = QRadioButton(self._lang.tr("settings.language.en"))
        self.lang_group = QButtonGroup(self)
        self.lang_group.addButton(self.lang_zh, 0)
        self.lang_group.addButton(self.lang_en, 1)

        if self._lang.lang == "zh":
            self.lang_zh.setChecked(True)
        else:
            self.lang_en.setChecked(True)

        lang_layout = QHBoxLayout()
        lang_layout.setSpacing(24)
        lang_layout.addWidget(self.lang_zh)
        lang_layout.addWidget(self.lang_en)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # ── Divider ──
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        # ── General section ──
        self.general_section = QLabel(self._lang.tr("settings.general"))
        layout.addWidget(self.general_section)

        # Default output directory
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(8)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText(self._lang.tr("settings.output_dir_placeholder"))
        self.output_dir_input.setText(get_default_output_dir())
        dir_layout.addWidget(self.output_dir_input, 1)

        self.browse_btn = QPushButton(self._lang.tr("label.browse"))
        self.browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(self.browse_btn)
        layout.addLayout(dir_layout)

        # Auto-open directory after processing
        self.auto_open_check = QCheckBox(self._lang.tr("settings.auto_open_dir"))
        self.auto_open_check.setChecked(get_auto_open_dir())
        layout.addWidget(self.auto_open_check)

        # Auto-check for updates
        self.auto_check_update = QCheckBox(self._lang.tr("update.auto_check"))
        self.auto_check_update.setChecked(get_auto_check_update())
        layout.addWidget(self.auto_check_update)

        # Manual check for updates
        check_row = QHBoxLayout()
        check_row.setSpacing(8)
        self.check_update_btn = QPushButton(self._lang.tr("update.check_now"))
        self.check_update_btn.clicked.connect(self._on_check_updates)
        self._check_status = QLabel("")
        check_row.addWidget(self.check_update_btn)
        check_row.addWidget(self._check_status)
        check_row.addStretch()
        layout.addLayout(check_row)

        # Hint for non-frozen environment
        self._frozen_hint = QLabel(
            self._lang.tr("update.frozen_required") if not is_frozen() else "")
        self._frozen_hint.setVisible(not is_frozen())
        layout.addWidget(self._frozen_hint)

        layout.addStretch()

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton(self._lang.tr("btn.cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(self._lang.tr("btn.save"))
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        # Ref lists for style/lang refresh
        self._section_labels = [self.lang_section, self.general_section]
        self._settings_labels = [self.auto_open_check]

    def _browse_output_dir(self):
        start = self.output_dir_input.text() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, self._lang.tr("label.select_dir"), start)
        if path:
            self.output_dir_input.setText(path)

    def _on_save(self):
        new_lang = "zh" if self.lang_zh.isChecked() else "en"
        self._lang.set_lang(new_lang)

        out_dir = self.output_dir_input.text().strip()
        set_default_output_dir(out_dir)

        set_auto_open_dir(self.auto_open_check.isChecked())
        set_auto_check_update(self.auto_check_update.isChecked())
        self.accept()

    def _on_check_updates(self):
        self._check_status.setText(self._lang.tr("update.checking"))
        self.check_updates_requested.emit()

    def set_check_status(self, text: str):
        self._check_status.setText(text)

    def _apply_styles(self):
        c = self._theme.current_colors

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['BG_CARD']};
                border: 1px solid {c['BORDER']};
                border-radius: {c['RADIUS_LG']}px;
            }}
        """)

        self.title_label.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {c['TEXT_PRIMARY']};"
        )

        for lbl in self._section_labels:
            lbl.setStyleSheet(
                f"font-size: 10pt; font-weight: bold; color: {c['PRIMARY']};"
            )

        radio_style = f"""
            QRadioButton {{
                color: {c['TEXT_PRIMARY']};
                font-size: 10pt;
                spacing: 6px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid {c['BORDER']};
            }}
            QRadioButton::indicator:checked {{
                border-color: {c['PRIMARY']};
                background-color: {c['PRIMARY']};
            }}
        """
        self.lang_zh.setStyleSheet(radio_style)
        self.lang_en.setStyleSheet(radio_style)

        input_style = f"""
            QLineEdit {{
                background-color: {c['BG_INPUT']};
                border: 1px solid {c['BORDER']};
                border-radius: {c['RADIUS_SM']}px;
                padding: 6px 10px;
                color: {c['TEXT_PRIMARY']};
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border-color: {c['PRIMARY']};
            }}
        """
        self.output_dir_input.setStyleSheet(input_style)

        self.auto_open_check.setStyleSheet(
            f"QCheckBox {{ color: {c['TEXT_PRIMARY']}; font-size: 10pt; spacing: 8px; }} "
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; "
            f"border: 2px solid {c['BORDER']}; }} "
            f"QCheckBox::indicator:checked {{ border-color: {c['PRIMARY']}; "
            f"background-color: {c['PRIMARY']}; }}"
        )
        self.auto_check_update.setStyleSheet(
            f"QCheckBox {{ color: {c['TEXT_PRIMARY']}; font-size: 10pt; spacing: 8px; }} "
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; "
            f"border: 2px solid {c['BORDER']}; }} "
            f"QCheckBox::indicator:checked {{ border-color: {c['PRIMARY']}; "
            f"background-color: {c['PRIMARY']}; }}"
        )

        self._check_status.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 9pt;")
        if hasattr(self, '_frozen_hint') and self._frozen_hint.isVisible():
            self._frozen_hint.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 9pt;")

        browse_style = f"""
            QPushButton {{
                color: {c['TEXT_SECONDARY']};
                border: 1px solid {c['BORDER']};
                border-radius: {c['RADIUS_SM']}px;
                padding: 6px 12px;
                font-size: 10pt;
                background: transparent;
            }}
            QPushButton:hover {{ border-color: {c['PRIMARY']}; }}
        """
        self.browse_btn.setStyleSheet(browse_style)
        self.check_update_btn.setStyleSheet(browse_style)

        btn_base = f"""
            QPushButton {{
                padding: 6px 20px;
                border-radius: {c['RADIUS_SM']}px;
                font-size: 10pt;
            }}
        """
        self.cancel_btn.setStyleSheet(
            btn_base +
            f"QPushButton {{ color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; background: transparent; }} "
            f"QPushButton:hover {{ border-color: {c['TEXT_PRIMARY']}; }}"
        )
        self.save_btn.setStyleSheet(
            btn_base +
            f"QPushButton {{ color: white; background-color: {c['PRIMARY']}; border: none; }} "
            f"QPushButton:hover {{ background-color: {c['PRIMARY_HOVER']}; }}"
        )

    def _on_theme_changed(self, _name):
        self._apply_styles()

    def _on_lang_changed(self, _lang):
        self.setWindowTitle(self._lang.tr("settings.title"))
        self.title_label.setText(self._lang.tr("settings.title"))
        self.lang_section.setText(self._lang.tr("settings.language"))
        self.lang_zh.setText(self._lang.tr("settings.language.zh"))
        self.lang_en.setText(self._lang.tr("settings.language.en"))
        self.general_section.setText(self._lang.tr("settings.general"))
        self.output_dir_input.setPlaceholderText(self._lang.tr("settings.output_dir_placeholder"))
        self.browse_btn.setText(self._lang.tr("label.browse"))
        self.auto_open_check.setText(self._lang.tr("settings.auto_open_dir"))
        self.auto_check_update.setText(self._lang.tr("update.auto_check"))
        self.check_update_btn.setText(self._lang.tr("update.check_now"))
        if hasattr(self, '_frozen_hint'):
            self._frozen_hint.setText(self._lang.tr("update.frozen_required"))
        self.cancel_btn.setText(self._lang.tr("btn.cancel"))
        self.save_btn.setText(self._lang.tr("btn.save"))
