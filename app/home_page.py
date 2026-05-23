"""首页 — 功能卡片导航"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QScrollArea
from PySide6.QtCore import Signal, Qt

from app.theme_manager import ThemeManager

FEATURE_GROUPS = {
    "数据处理": [
        {"id": "split", "icon": "✂️", "title": "表格拆分",
         "desc": "按指定字段拆分为独立文件或多个 Sheet"},
        {"id": "merge", "icon": "\U0001f517", "title": "表格合并",
         "desc": "多文件合并为一个或多 Sheet 合并"},
        {"id": "dedup", "icon": "\U0001f9f9", "title": "数据去重",
         "desc": "按指定列检测并删除重复数据行"},
        {"id": "convert", "icon": "\U0001f504", "title": "格式转换",
         "desc": "XLSX / CSV 批量互转"},
    ],
    "数据分析": [
        {"id": "filter", "icon": "\U0001f50d", "title": "数据筛选",
         "desc": "按条件过滤行，支持 11 种运算符"},
        {"id": "columns", "icon": "\U0001f4cb", "title": "列操作",
         "desc": "重排、重命名、删除列及计算列"},
        {"id": "pivot", "icon": "\U0001f4ca", "title": "透视表",
         "desc": "交叉表分析，求和/计数/平均"},
        {"id": "validate", "icon": "✅", "title": "数据校验",
         "desc": "空值检测、异常值发现、类型检查"},
    ],
}


class FeatureCard(QFrame):
    clicked = Signal(str)

    def __init__(self, feature_id: str, icon: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self._id = feature_id
        self._theme = ThemeManager.instance()
        self.setCursor(Qt.PointingHandCursor)

        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("font-size: 28px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(36)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("font-size: 8.5pt;")
        self.desc_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)

        self._apply_style()
        self._theme.theme_changed.connect(self._on_theme_changed)

    def _apply_style(self):
        c = self._theme.current_colors
        self.setStyleSheet(
            f"FeatureCard {{ background: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_MD']}px; padding: 12px; }} "
            f"FeatureCard:hover {{ border-color: {c['PRIMARY']}; background: {c['PRIMARY_LIGHT']}; }}"
        )
        self.title_label.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {c['TEXT_PRIMARY']};")
        self.desc_label.setStyleSheet(f"font-size: 8.5pt; color: {c['TEXT_SECONDARY']};")

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self._id)


class HomePage(QWidget):
    feature_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._section_labels = []
        self._setup_ui()
        self._theme.theme_changed.connect(self._on_theme_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(10)

        # 标题
        self.title = QLabel("GridFlow")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)

        self.subtitle = QLabel("表格数据流式处理，轻量、快速、离线可用")
        self.subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle)

        layout.addSpacing(6)

        # 双列分组布局
        outer = QHBoxLayout()
        outer.setSpacing(20)

        self._cards = []
        for group_name, features in FEATURE_GROUPS.items():
            col = QVBoxLayout()
            col.setSpacing(6)

            # 分区标题
            section_hdr = QLabel(group_name)
            section_hdr.setAlignment(Qt.AlignCenter)
            self._section_labels.append(section_hdr)
            col.addWidget(section_hdr)

            for feat in features:
                card = FeatureCard(feat["id"], feat["icon"], feat["title"], feat["desc"])
                card.clicked.connect(lambda fid=feat["id"]: self.feature_selected.emit(fid))
                col.addWidget(card)
                self._cards.append(card)

            col.addStretch()
            outer.addLayout(col)

        # 包裹在滚动区
        inner = QWidget()
        inner.setLayout(outer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        layout.addWidget(scroll, 1)

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
        for lbl in self._section_labels:
            lbl.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {c['PRIMARY']}; padding: 2px 0;")

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()
