"""首页 — 功能卡片导航"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PySide6.QtCore import Signal, Qt

from app.theme import (
    PRIMARY, PRIMARY_LIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER, BG_MAIN, BG_CARD, RADIUS_MD,
)

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
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"FeatureCard {{ background: {BG_CARD}; border: 1px solid {BORDER}; "
            f"border-radius: {RADIUS_MD}px; padding: 20px; }} "
            f"FeatureCard:hover {{ border-color: {PRIMARY}; background: {PRIMARY_LIGHT}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 12pt; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"font-size: 9pt; color: {TEXT_SECONDARY};")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self._id)


class HomePage(QWidget):
    feature_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # 标题
        title = QLabel("GridFlow")
        title.setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("表格数据流式处理，轻量、快速、离线可用")
        subtitle.setStyleSheet(f"font-size: 10pt; color: {TEXT_MUTED};")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        # 2×2 卡片网格
        grid = QGridLayout()
        grid.setSpacing(16)

        for i, feat in enumerate(FEATURES):
            card = FeatureCard(feat["id"], feat["icon"], feat["title"], feat["desc"])
            card.clicked.connect(lambda fid=feat["id"]: self.feature_selected.emit(fid))
            row, col = divmod(i, 2)
            grid.addWidget(card, row, col)
            grid.setRowStretch(row, 1)
            grid.setColumnStretch(col, 1)

        layout.addLayout(grid)

        layout.addStretch()

        # 版本
        ver = QLabel("v2.0")
        ver.setStyleSheet(f"font-size: 8pt; color: {TEXT_MUTED};")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)
