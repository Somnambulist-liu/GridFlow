import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QStackedWidget, QPushButton, QApplication, QLabel, QDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

from app.theme_manager import ThemeManager
from app.styles import build_global_stylesheet
from app.home_page import HomePage
from app.pipeline import PipelineContext
from app.i18n import LangManager, APP_VERSION
from app.settings_dialog import SettingsDialog
from app.settings import get_auto_check_update, get_ignored_version
from app.updater import (
    is_frozen, should_auto_check, set_last_check_time,
    UpdateChecker, UpdateDownloader, UpdateDialog, apply_update_and_restart,
)


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

        # Auto-check for updates 3 seconds after startup
        QTimer.singleShot(3000, self._startup_check)

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

        self.update_btn.setToolTip(self._lang.tr("update.check_now"))
        self.update_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 4px 10px; font-size: 12pt; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; }} "
            f"QPushButton:disabled {{ color: {c['TEXT_MUTED']}; }}"
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

        self.update_btn = QPushButton("\U0001F504")
        self.update_btn.setToolTip(self._lang.tr("update.check_now"))
        self.update_btn.clicked.connect(lambda: self._check_updates())
        header_layout.addWidget(self.update_btn)

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
        dlg.check_updates_requested.connect(lambda: self._check_updates(status_label=dlg))
        dlg.exec()

    # ── Update checking ─────────────────────────────────

    def _check_updates(self, *, status_label=None):
        """Check GitHub for newer releases."""
        self._checker = UpdateChecker(APP_VERSION, self)
        self._checker.up_to_date.connect(lambda: self._on_up_to_date(status_label))
        self._checker.update_available.connect(
            lambda info: self._on_update_available(info, status_label))
        self._checker.error_occurred.connect(
            lambda msg: self._on_check_error(msg, status_label))
        self._checker.start()

    def _on_up_to_date(self, status_label=None):
        if status_label:
            from app.settings_dialog import SettingsDialog
            if isinstance(status_label, SettingsDialog):
                status_label.set_check_status(self._lang.tr("update.up_to_date"))
        # Record check time for cache
        set_last_check_time()

    def _on_update_available(self, info: dict, status_label=None):
        set_last_check_time()
        if status_label:
            from app.settings_dialog import SettingsDialog
            if isinstance(status_label, SettingsDialog):
                status_label.set_check_status(
                    f"{self._lang.tr('update.latest')}: {info['version']}")
        # Skip if this version was ignored
        ignored = get_ignored_version()
        if ignored and ignored == info["version"]:
            return
        # Show dialog
        dlg = UpdateDialog(info, APP_VERSION, self._lang, self)
        if dlg.exec() == QDialog.Accepted:
            self._download_update(info)

    def _on_check_error(self, msg: str, status_label=None):
        if msg == "not frozen":
            display = self._lang.tr("update.frozen_required")
        else:
            display = f"{self._lang.tr('update.error')}: {msg}"
        if status_label:
            from app.settings_dialog import SettingsDialog
            if isinstance(status_label, SettingsDialog):
                status_label.set_check_status(display)
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, self._lang.tr("update.check_now"), display)

    def _download_update(self, info: dict):
        self._downloader = UpdateDownloader(info["download_url"], info.get("size", 0), self)
        # Show a simple progress bar dialog
        from PySide6.QtWidgets import QProgressDialog
        progress = QProgressDialog(
            self._lang.tr("update.downloading"), "", 0, 100, self)
        progress.setWindowTitle(self._lang.tr("update.download"))
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setCancelButton(None)
        progress.setModal(True)
        progress.show()

        def on_progress(cur, total):
            if total > 0:
                progress.setMaximum(total)
                progress.setValue(cur)

        def on_finished(path):
            progress.close()
            apply_update_and_restart(path)

        def on_error(msg):
            progress.close()

        self._downloader.progress.connect(on_progress)
        self._downloader.finished.connect(on_finished)
        self._downloader.error_occurred.connect(on_error)
        self._downloader.start()

    # ── Startup auto‑check ──────────────────────────────

    def _startup_check(self):
        """Called after the window is shown, if auto‑check is enabled."""
        if not is_frozen():
            return
        if not get_auto_check_update():
            return
        if not should_auto_check():
            return
        self._check_updates()
