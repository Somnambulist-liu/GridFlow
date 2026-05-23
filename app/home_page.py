"""首页 — 功能卡片导航，分组展示"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Signal, Qt

from app.theme_manager import ThemeManager
from app.i18n import LangManager

FEATURE_GROUPS = [
    {
        "group_key": "home.group.data",
        "features": [
            {"id": "split", "icon": "✂️", "title_key": "card.split", "desc_key": "card.split.desc"},
            {"id": "merge", "icon": "\U0001f517", "title_key": "card.merge", "desc_key": "card.merge.desc"},
            {"id": "dedup", "icon": "\U0001f9f9", "title_key": "card.dedup", "desc_key": "card.dedup.desc"},
            {"id": "convert", "icon": "\U0001f504", "title_key": "card.convert", "desc_key": "card.convert.desc"},
        ]
    },
    {
        "group_key": "home.group.analysis",
        "features": [
            {"id": "filter", "icon": "\U0001f50d", "title_key": "card.filter", "desc_key": "card.filter.desc"},
            {"id": "columns", "icon": "\U0001f4cb", "title_key": "card.columns", "desc_key": "card.columns.desc"},
            {"id": "pivot", "icon": "\U0001f4ca", "title_key": "card.pivot", "desc_key": "card.pivot.desc"},
            {"id": "validate", "icon": "✅", "title_key": "card.validate", "desc_key": "card.validate.desc"},
        ]
    },
]


class FeatureCard(QFrame):
    clicked = Signal(str)

    def __init__(self, feature_id: str, icon: str, title_key: str, desc_key: str, parent=None):
        super().__init__(parent)
        self._id = feature_id
        self._title_key = title_key
        self._desc_key = desc_key
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self.setCursor(Qt.PointingHandCursor)

        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("font-size: 28px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(36)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("font-size: 8.5pt;")
        self.desc_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)

        self._apply_lang()
        self._apply_style()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    def _apply_lang(self):
        self.title_label.setText(self._lang.tr(self._title_key))
        self.desc_label.setText(self._lang.tr(self._desc_key))

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

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def mousePressEvent(self, event):
        self.clicked.emit(self._id)


class HomePage(QWidget):
    feature_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._section_labels = []
        self._cards = []
        self._setup_ui()
        self._apply_lang()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 20)
        layout.setSpacing(12)

        # 双列分组布局
        outer = QHBoxLayout()
        outer.setSpacing(20)

        for group in FEATURE_GROUPS:
            col = QVBoxLayout()
            col.setSpacing(6)

            section_hdr = QLabel()
            section_hdr.setAlignment(Qt.AlignCenter)
            self._section_labels.append((section_hdr, group["group_key"]))
            col.addWidget(section_hdr)

            for feat in group["features"]:
                card = FeatureCard(feat["id"], feat["icon"], feat["title_key"], feat["desc_key"])
                card.clicked.connect(lambda fid=feat["id"]: self.feature_selected.emit(fid))
                col.addWidget(card)
                self._cards.append(card)

            col.addStretch()
            outer.addLayout(col)

        inner = QWidget()
        inner.setLayout(outer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        layout.addWidget(scroll, 1)

        self.ver = QLabel()
        self.ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ver)

        self._apply_style()

    def _apply_lang(self):
        for lbl, key in self._section_labels:
            lbl.setText(self._lang.tr(key))
        self.ver.setText(self._lang.tr("app.version"))

    def _apply_style(self):
        c = self._theme.current_colors
        for lbl, _ in self._section_labels:
            lbl.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {c['PRIMARY']}; padding: 2px 0;")
        self.ver.setStyleSheet(f"font-size: 8pt; color: {c['TEXT_MUTED']}; margin-top: 4px;")

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()
