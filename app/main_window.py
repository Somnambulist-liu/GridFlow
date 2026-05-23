import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QStackedWidget, QPushButton, QApplication, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.theme_manager import ThemeManager
from app.styles import build_global_stylesheet
from app.home_page import HomePage
from app.pipeline import PipelineContext
from app.i18n import LangManager, APP_VERSION
from app.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    FEATURE_INDEX = {"split": 1, "merge": 2, "dedup": 3, "convert": 4, "filter": 5, "columns": 6, "pivot": 7, "validate": 8}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GridFlow")
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self.pipeline = PipelineContext(self)

        base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
        icon_ext = "ico" if sys.platform == "win32" else "png"
        icon_path = os.path.join(base, "resources", f"icon.{icon_ext}")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(680, 700)
        self.resize(780, 760)

        self._apply_global_theme()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

        self._active_feature = None
        self._feature_widgets = {}

        self._setup_ui()
        self._connect_signals()

    def _apply_global_theme(self):
        c = self._theme.current_colors
        QApplication.instance().setStyleSheet(build_global_stylesheet(c))

    def _refresh_header(self):
        c = self._theme.current_colors
        self.header.setStyleSheet(
            f"background-color: {c['BG_CARD']}; border-bottom: 1px solid {c['BORDER']};"
        )

        self.back_btn.setText(self._lang.tr("btn.back"))
        self.back_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {c['PRIMARY']}; "
            f"border: 1px solid {c['PRIMARY']}; border-radius: {c['RADIUS_SM']}px; "
            f"padding: 4px 16px; font-size: 10pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {c['PRIMARY']}; color: white; }}"
        )

        self.title_label.setText(self._lang.tr("app.title"))
        self.title_label.setStyleSheet(
            f"font-size: 12pt; font-weight: bold; color: {c['TEXT_PRIMARY']};"
        )
        self.version_label.setStyleSheet(
            f"font-size: 9pt; color: {c['TEXT_MUTED']};"
        )
        self.subtitle_label.setText(self._lang.tr("app.subtitle"))
        self.subtitle_label.setStyleSheet(
            f"font-size: 9pt; color: {c['TEXT_MUTED']};"
        )

        self.settings_btn.setText(self._lang.tr("btn.settings"))
        self.settings_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 4px 10px; font-size: 12pt; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; }}"
        )

        theme_labels = {
            "light": self._lang.tr("theme.light"),
            "dark": self._lang.tr("theme.dark"),
            "auto": self._lang.tr("theme.auto"),
        }
        self.theme_btn.setText(theme_labels.get(self._theme.theme, self._lang.tr("theme.light")))
        self.theme_btn.setToolTip(self._lang.tr("theme.tooltip"))
        self.theme_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 4px 14px; font-size: 10pt; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; }}"
        )

    def _on_theme_changed(self, _theme_name: str):
        self._apply_global_theme()
        self._refresh_header()

    def _on_lang_changed(self, _lang: str):
        self._refresh_header()
        self.setWindowTitle(self._lang.tr("app.title"))

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 头部 ──
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(8)

        self.back_btn = QPushButton()
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_home)
        header_layout.addWidget(self.back_btn)

        header_layout.addStretch()

        # Title block: app name  version  ·  subtitle
        self.title_label = QLabel()
        self.version_label = QLabel()
        self.subtitle_label = QLabel()

        title_wrap = QWidget()
        title_layout = QHBoxLayout(title_wrap)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.version_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addWidget(title_wrap)

        header_layout.addStretch()

        self.settings_btn = QPushButton()
        self.settings_btn.setToolTip(self._lang.tr("btn.settings.tooltip"))
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        header_layout.addWidget(self.settings_btn)

        self.theme_btn = QPushButton()
        self.theme_btn.setToolTip(self._lang.tr("theme.tooltip"))
        self.theme_btn.clicked.connect(self._theme.toggle)
        header_layout.addWidget(self.theme_btn)

        root.addWidget(self.header)

        # ── 内容区 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: transparent;")

        self.home_page = HomePage()
        self.stack.addWidget(self.home_page)  # index 0

        root.addWidget(self.stack, 1)

        self._refresh_header()

    def _connect_signals(self):
        self.home_page.feature_selected.connect(self._on_feature_selected)

    def register_feature(self, feature_id: str, widget: QWidget):
        """注册功能模块"""
        self._feature_widgets[feature_id] = widget
        self.stack.addWidget(widget)

    def _on_feature_selected(self, feature_id: str):
        if feature_id not in self._feature_widgets:
            return
        self._active_feature = feature_id
        idx = self.FEATURE_INDEX.get(feature_id, 1)
        self.stack.setCurrentIndex(idx)
        self.back_btn.setVisible(True)

    def _go_home(self):
        self._active_feature = None
        self.stack.setCurrentIndex(0)
        self.back_btn.setVisible(False)

    def _on_settings_clicked(self):
        dlg = SettingsDialog(self)
        dlg.exec()
