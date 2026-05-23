"""首页 — 功能卡片导航"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QScrollArea
from PySide6.QtCore import Signal, Qt

from app.theme_manager import ThemeManager

FEATURES = [
    {
        "id": "split",
        "icon": "✂️",
        "title": "表格拆分",
        "desc": "按指定字段拆分为独立文件\n或多个 Sheet",
    },
    {
        "id": "merge",
        "icon": "\U0001f517",
        "title": "表格合并",
        "desc": "多文件合并为一个\n或多 Sheet 合并",
    },
    {
        "id": "dedup",
        "icon": "\U0001f9f9",
        "title": "数据去重",
        "desc": "按指定列检测并删除\n重复数据行",
    },
    {
        "id": "convert",
        "icon": "\U0001f504",
        "title": "格式转换",
        "desc": "XLSX / CSV\n批量互转",
    },
]


class FeatureCard(QFrame):
    clicked = Signal(str)

    def __init__(self, feature_id: str, icon: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self._id = feature_id
        self._icon = icon
        self._title = title
        self._desc = desc
        self._theme = ThemeManager.instance()
        self.setCursor(Qt.PointingHandCursor)

        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("font-size: 32px;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("font-size: 9pt;")
        self.desc_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)

        self._apply_style()
        self._theme.theme_changed.connect(self._on_theme_changed)

    def _apply_style(self):
        c = self._theme.current_colors
        self.setStyleSheet(
            f"FeatureCard {{ background: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_MD']}px; padding: 20px; }} "
            f"FeatureCard:hover {{ border-color: {c['PRIMARY']}; background: {c['PRIMARY_LIGHT']}; }}"
        )
        self.title_label.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {c['TEXT_PRIMARY']};")
        self.desc_label.setStyleSheet(f"font-size: 9pt; color: {c['TEXT_SECONDARY']};")

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self._id)


class HomePage(QWidget):
    feature_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._setup_ui()
        self._theme.theme_changed.connect(self._on_theme_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # 标题
        self.title = QLabel("GridFlow")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)

        self.subtitle = QLabel("表格数据流式处理，轻量、快速、离线可用")
        self.subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle)

        layout.addSpacing(12)

        # 2×2 卡片网格
        grid = QGridLayout()
        grid.setSpacing(16)

        self._cards = []
        for i, feat in enumerate(FEATURES):
            card = FeatureCard(feat["id"], feat["icon"], feat["title"], feat["desc"])
            card.clicked.connect(lambda fid=feat["id"]: self.feature_selected.emit(fid))
            row, col = divmod(i, 2)
            grid.addWidget(card, row, col)
            grid.setRowStretch(row, 1)
            grid.setColumnStretch(col, 1)
            self._cards.append(card)

        layout.addLayout(grid)
        layout.addStretch()

        # 版本
        self.ver = QLabel("v3.0")
        self.ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ver)

        self._apply_style()

    def _apply_style(self):
        c = self._theme.current_colors
        self.title.setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {c['TEXT_PRIMARY']};")
        self.subtitle.setStyleSheet(f"font-size: 10pt; color: {c['TEXT_MUTED']};")
        self.ver.setStyleSheet(f"font-size: 8pt; color: {c['TEXT_MUTED']};")

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()
