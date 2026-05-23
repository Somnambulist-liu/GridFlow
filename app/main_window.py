import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.styles import GLOBAL_STYLESHEET
from app.theme import PRIMARY, PRIMARY_HOVER, TEXT_MUTED, BORDER, RADIUS_SM, BG_CARD, TEXT_PRIMARY
from app.home_page import HomePage


class MainWindow(QMainWindow):
    FEATURE_INDEX = {"split": 1, "merge": 2, "dedup": 3, "convert": 4}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GridFlow")
        base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
        icon_path = os.path.join(base, "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(680, 580)
        self.resize(720, 620)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        self._active_feature = None
        self._feature_widgets = {}

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 头部 ──
        self.header = QWidget()
        self.header.setStyleSheet(f"background-color: {BG_CARD}; border-bottom: 1px solid {BORDER};")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        self.back_btn = QPushButton("←  首页")
        self.back_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {PRIMARY}; "
            f"border: 1px solid {PRIMARY}; border-radius: {RADIUS_SM}px; "
            f"padding: 4px 16px; font-size: 10pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY}; color: white; }}"
        )
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_home)
        header_layout.addWidget(self.back_btn)

        header_layout.addStretch()

        self.title_label = QLabel("GridFlow")
        self.title_label.setStyleSheet(f"font-size: 13pt; font-weight: bold; color: {TEXT_PRIMARY};")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        header_layout.addWidget(QWidget())  # spacer to balance back_btn width
        root.addWidget(self.header)

        # ── 内容区 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: transparent;")

        self.home_page = HomePage()
        self.stack.addWidget(self.home_page)  # index 0

        root.addWidget(self.stack, 1)

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
        self.title_label.setText(self._get_title(feature_id))

    def _go_home(self):
        self._active_feature = None
        self.stack.setCurrentIndex(0)
        self.back_btn.setVisible(False)
        self.title_label.setText("GridFlow")

    @staticmethod
    def _get_title(feature_id: str) -> str:
        titles = {
            "split": "表格拆分",
            "merge": "表格合并",
            "dedup": "数据去重",
            "convert": "格式转换",
        }
        return titles.get(feature_id, "")
