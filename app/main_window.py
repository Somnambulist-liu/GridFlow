import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QStackedWidget, QPushButton, QApplication, QLabel, QDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

from app.theme_manager import ThemeManager
from app.styles import build_global_stylesheet
from app.home_page import HomePage
from app.pipeline import PipelineContext
from app.i18n import LangManager, APP_VERSION
from app.resources import icon_path
# app.updater / app.settings_dialog 只在真正需要时才导入（自动更新、设置弹窗），
# 它们会把 http.client、subprocess 等模块拖进启动路径。


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GridFlow")
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self.pipeline = PipelineContext(self)

        icon = icon_path()
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.setMinimumSize(680, 700)
        self.resize(780, 760)

        self._apply_global_theme()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

        self._active_feature = None
        self._feature_factories = {}   # feature_id -> 构造该页面的工厂
        self._feature_widgets = {}     # feature_id -> 已创建的页面
        self._feature_order = []       # 注册顺序，用于 Ctrl+1..8

        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # Auto-check for updates 3 seconds after startup
        QTimer.singleShot(3000, self._startup_check)

    # ── 快捷键 ──────────────────────────────────────────

    # 各功能页“选择文件”按钮的属性名（用于 Ctrl+O 转发）
    BROWSE_BUTTON_ATTRS = ("browse_btn", "add_files_btn", "add_btn", "file_btn", "sheet_file_btn")

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self._on_settings_clicked)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self._go_home)
        QShortcut(QKeySequence("Escape"), self, activated=self._go_home)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_file_shortcut)
        for index in range(9):
            QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self,
                      activated=lambda i=index: self._open_feature_by_index(i))

    def _open_feature_by_index(self, index: int):
        if 0 <= index < len(self._feature_order):
            self._on_feature_selected(self._feature_order[index])

    def _open_file_shortcut(self):
        """Ctrl+O：转发给当前功能页上的“选择文件”按钮。"""
        widget = self._feature_widgets.get(self._active_feature)
        if widget is None:
            return
        targets = [widget, getattr(widget, "step1", None)]
        for target in targets:
            if target is None:
                continue
            for attr in self.BROWSE_BUTTON_ATTRS:
                button = getattr(target, attr, None)
                if isinstance(button, QPushButton) and button.isEnabled() and button.isVisible():
                    button.click()
                    return

    def _apply_global_theme(self):
        c = self._theme.current_colors
        QApplication.instance().setStyleSheet(build_global_stylesheet(c))

    def _header_btn_style(self, c, font_size: str = "10pt") -> str:
        """header 上三个图标按钮统一尺寸、边框与焦点态。"""
        return (
            f"QPushButton {{ background-color: transparent; color: {c['TEXT_PRIMARY']}; "
            f"border: 1px solid {c['BORDER']}; border-radius: {c['RADIUS_SM']}px; "
            f"padding: 3px 12px; font-size: {font_size}; }} "
            f"QPushButton:hover {{ border-color: {c['PRIMARY']}; color: {c['PRIMARY']}; }} "
            f"QPushButton:pressed {{ background-color: {c['PRIMARY_LIGHT']}; }} "
            f"QPushButton:focus {{ border: 2px solid {c['PRIMARY']}; }} "
            f"QPushButton:disabled {{ color: {c['TEXT_MUTED']}; }}"
        )

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
            f"QPushButton:hover {{ background-color: {c['PRIMARY']}; color: white; }} "
            f"QPushButton:focus {{ border: 2px solid {c['PRIMARY_HOVER']}; }}"
        )

        self.title_label.setText(self._lang.tr("app.title"))
        self.title_label.setStyleSheet(
            f"font-size: 12pt; font-weight: bold; color: {c['TEXT_PRIMARY']};"
        )
        # 版本号放在标题旁（以前 header 里这个标签是空的、版本另占底部一行）
        self.version_label.setText(self._lang.tr("app.version"))
        self.version_label.setStyleSheet(
            f"font-size: 9pt; color: {c['TEXT_MUTED']}; padding-top: 3px;"
        )
        self.subtitle_label.setText(self._lang.tr("app.subtitle"))
        self.subtitle_label.setStyleSheet(
            f"font-size: 9pt; color: {c['TEXT_MUTED']};"
        )

        btn_style = self._header_btn_style(c)
        self.settings_btn.setText(self._lang.tr("btn.settings"))
        self.settings_btn.setStyleSheet(btn_style)

        # 按钮上显示“当前”主题，图标与文字一致（以前浅色配月亮图标，容易读反）
        theme_labels = {
            "light": self._lang.tr("theme.light"),
            "dark": self._lang.tr("theme.dark"),
            "auto": self._lang.tr("theme.auto"),
        }
        self.theme_btn.setText(theme_labels.get(self._theme.theme, self._lang.tr("theme.light")))
        self.theme_btn.setToolTip(self._lang.tr("theme.tooltip"))
        self.theme_btn.setStyleSheet(btn_style)

        self.update_btn.setText("\U0001F504")
        self.update_btn.setToolTip(self._lang.tr("update.check_now"))
        self.update_btn.setStyleSheet(self._header_btn_style(c, font_size="11pt"))

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
        self.settings_btn.setFixedHeight(30)
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        header_layout.addWidget(self.settings_btn)

        self.theme_btn = QPushButton()
        self.theme_btn.setToolTip(self._lang.tr("theme.tooltip"))
        self.theme_btn.setFixedHeight(30)
        self.theme_btn.clicked.connect(self._theme.toggle)
        header_layout.addWidget(self.theme_btn)

        self.update_btn = QPushButton("\U0001F504")
        self.update_btn.setToolTip(self._lang.tr("update.check_now"))
        self.update_btn.setFixedHeight(30)
        self.update_btn.setFixedWidth(36)
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

    def register_feature(self, feature_id: str, factory):
        """注册功能模块。

        ``factory`` 可以是构造页面的可调用对象（惰性创建，首次进入才建 UI），
        也可以直接传一个已创建好的 QWidget（兼容旧调用方式）。
        """
        if feature_id not in self._feature_order:
            self._feature_order.append(feature_id)
        if isinstance(factory, QWidget):
            self._feature_widgets[feature_id] = factory
            self.stack.addWidget(factory)
        else:
            self._feature_factories[feature_id] = factory

    def _ensure_feature(self, feature_id: str):
        """按需创建功能页面并加入 stack。"""
        widget = self._feature_widgets.get(feature_id)
        if widget is not None:
            return widget
        factory = self._feature_factories.get(feature_id)
        if factory is None:
            return None
        widget = factory()
        self._feature_widgets[feature_id] = widget
        self.stack.addWidget(widget)
        return widget

    def _on_feature_selected(self, feature_id: str):
        widget = self._ensure_feature(feature_id)
        if widget is None:
            return
        self._active_feature = feature_id
        self.stack.setCurrentWidget(widget)
        self.back_btn.setVisible(True)

    def _go_home(self):
        self._active_feature = None
        self.stack.setCurrentIndex(0)
        self.back_btn.setVisible(False)

    def _on_settings_clicked(self):
        from app.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self)
        dlg.check_updates_requested.connect(lambda: self._check_updates(status_label=dlg))
        dlg.exec()

    # ── Update checking ─────────────────────────────────

    def _check_updates(self, *, status_label=None):
        """Check GitHub for newer releases."""
        from app.updater import UpdateChecker

        self._checker = UpdateChecker(APP_VERSION, self)
        self._checker.up_to_date.connect(lambda: self._on_up_to_date(status_label))
        self._checker.update_available.connect(
            lambda info: self._on_update_available(info, status_label))
        self._checker.error_occurred.connect(
            lambda msg: self._on_check_error(msg, status_label))
        self._checker.start()

    def _set_status_safely(self, status_label, text: str):
        """把检查结果回填到设置对话框；对话框可能已经被关闭。"""
        if not status_label:
            return False
        try:
            status_label.set_check_status(text)
            return True
        except RuntimeError:          # 底层 C++ 对象已销毁
            return False

    def _on_up_to_date(self, status_label=None):
        from app.updater import set_last_check_time

        self._set_status_safely(status_label, self._lang.tr("update.up_to_date"))
        # Record check time for cache
        set_last_check_time()

    def _on_update_available(self, info: dict, status_label=None):
        from app.settings import get_ignored_version
        from app.updater import set_last_check_time, UpdateDialog

        set_last_check_time()
        self._set_status_safely(
            status_label, f"{self._lang.tr('update.latest')}: {info['version']}")
        # Skip if this version was ignored
        ignored = get_ignored_version()
        if ignored and ignored == info["version"]:
            return
        # 下载与安装都由对话框自己接管（发现新版本 → 下载中 → 准备安装）
        dialog = UpdateDialog(info, APP_VERSION, self._lang, self)
        dialog.exec()

    def _on_check_error(self, msg: str, status_label=None):
        if msg == "not frozen":
            display = self._lang.tr("update.frozen_required")
        else:
            display = f"{self._lang.tr('update.error')}: {msg}"
        if not self._set_status_safely(status_label, display):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, self._lang.tr("update.check_now"), display)

    # ── Startup auto‑check ──────────────────────────────

    def _startup_check(self):
        """Called after the window is shown, if auto‑check is enabled."""
        from app.settings import get_auto_check_update
        from app.updater import is_frozen, should_auto_check

        if not is_frozen():
            return
        if not get_auto_check_update():
            return
        if not should_auto_check():
            return
        self._check_updates()
