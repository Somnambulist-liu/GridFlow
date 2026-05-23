"""Settings dialog — language switching and general preferences."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QRadioButton, QPushButton, QButtonGroup, QFrame,
)
from PySide6.QtCore import Qt

from app.theme_manager import ThemeManager
from app.i18n import LangManager


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()

        self.setWindowTitle(self._lang.tr("settings.title"))
        self.setMinimumWidth(380)
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
        lang_label = QLabel(self._lang.tr("settings.language"))
        lang_label.setStyleSheet("font-size: 10pt; font-weight: bold;")
        layout.addWidget(lang_label)

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
        general_label = QLabel(self._lang.tr("settings.general"))
        general_label.setStyleSheet("font-size: 10pt; font-weight: bold;")
        layout.addWidget(general_label)

        # Placeholder for future settings (output dir, etc.)
        placeholder = QLabel("—")
        placeholder.setStyleSheet("color: #94A3B8; font-size: 9pt;")
        layout.addWidget(placeholder)

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

        # Store refs for style refresh
        self._section_labels = [lang_label, general_label]

    def _on_save(self):
        new_lang = "zh" if self.lang_zh.isChecked() else "en"
        self._lang.set_lang(new_lang)
        self.accept()

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
        self.lang_zh.setText(self._lang.tr("settings.language.zh"))
        self.lang_en.setText(self._lang.tr("settings.language.en"))
        self.cancel_btn.setText(self._lang.tr("btn.cancel"))
        self.save_btn.setText(self._lang.tr("btn.save"))
