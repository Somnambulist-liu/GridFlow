"""首页 — 功能卡片导航，分组展示，随窗口宽度自适应列数"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QToolButton,
)
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtGui import QKeyEvent

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

# 版式常量：宽屏时内容区限宽并居中，避免卡片被拉成整屏宽
CONTENT_MAX_WIDTH = 1180
CARD_MIN_WIDTH = 240
GRID_GAP = 8
GROUP_GAP = 20
PAGE_MARGIN = 24


class FeatureCard(QFrame):
    """功能卡片：整卡可点，且支持键盘（Tab 聚焦、回车/空格触发）。"""

    clicked = Signal(str)

    def __init__(self, feature_id: str, icon: str, title_key: str, desc_key: str, parent=None):
        super().__init__(parent)
        self._id = feature_id
        self._title_key = title_key
        self._desc_key = desc_key
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()

        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)          # 让卡片进入 Tab 顺序
        self.setMinimumHeight(104)

        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("font-size: 30px; background: transparent;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(38)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 11.5pt; font-weight: bold; background: transparent;")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("font-size: 9.5pt; background: transparent;")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        # 不要给 layout 设 AlignCenter：那会让子控件只按 sizeHint 定宽（卡片被撑不满、
        # 文字挤成竖条）。这里用上下 stretch 实现垂直居中，宽度交给布局拉伸。
        layout.setSpacing(4)
        layout.addStretch(1)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
        layout.addStretch(1)

        self._apply_lang()
        self._apply_style()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    # ── 文案与样式 ──────────────────────────────────────

    def _apply_lang(self):
        title = self._lang.tr(self._title_key)
        desc = self._lang.tr(self._desc_key)
        self.title_label.setText(title)
        self.desc_label.setText(desc)
        self.setAccessibleName(title)
        self.setAccessibleDescription(desc)
        self.setToolTip(f"{title} — {desc}")

    def _apply_style(self):
        c = self._theme.current_colors
        self.setStyleSheet(
            f"FeatureCard {{ background: {c['BG_CARD']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_MD']}px; }} "
            f"FeatureCard:hover {{ border-color: {c['PRIMARY']}; background: {c['PRIMARY_LIGHT']}; }} "
            f"FeatureCard:focus {{ border: 2px solid {c['PRIMARY']}; }}"
        )
        self.title_label.setStyleSheet(
            f"font-size: 11.5pt; font-weight: bold; color: {c['TEXT_PRIMARY']}; background: transparent;")
        self.desc_label.setStyleSheet(
            f"font-size: 9.5pt; color: {c['TEXT_SECONDARY']}; background: transparent;")

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    # ── 交互 ────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self.clicked.emit(self._id)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit(self._id)
            event.accept()
            return
        super().keyPressEvent(event)


class HomePage(QWidget):
    feature_selected = Signal(str)

    WARNING_DISMISSED_KEY = "home/warning_dismissed"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._settings = QSettings("GridFlow", "GridFlow")
        self._section_labels = []
        self._cards = {}
        self._grids = []
        self._grid_columns = 0
        self._setup_ui()
        self._apply_lang()
        self._apply_style()
        self._update_grid()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    # ── 构建 ────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(PAGE_MARGIN, 12, PAGE_MARGIN, 16)
        inner_layout.setSpacing(0)
        # 上下留白：内容比视口矮时整体居中，而不是全都堆在顶部
        inner_layout.addStretch(1)

        content = QWidget()
        content.setMaximumWidth(CONTENT_MAX_WIDTH)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(GROUP_GAP)

        for group in FEATURE_GROUPS:
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(GRID_GAP)

            section_hdr = QLabel()
            section_hdr.setAlignment(Qt.AlignCenter)
            self._section_labels.append((section_hdr, group["group_key"]))
            box_layout.addWidget(section_hdr)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(GRID_GAP)
            box_layout.addLayout(grid)
            box_layout.addStretch(0)

            self._grids.append((grid, group))
            for feat in group["features"]:
                card = FeatureCard(feat["id"], feat["icon"], feat["title_key"], feat["desc_key"])
                card.clicked.connect(lambda fid=feat["id"]: self.feature_selected.emit(fid))
                self._cards[feat["id"]] = card

            content_layout.addWidget(box, 1)

        center_row = QHBoxLayout()
        center_row.setContentsMargins(0, 0, 0, 0)
        # 内容区自己吃满可用宽度（上限 CONTENT_MAX_WIDTH），两侧留白只吸收剩余空间，
        # 这样既不会被拉伸到整屏宽，也能在宽屏下真正居中。
        center_row.addStretch(0)
        center_row.addWidget(content, 1)
        center_row.addStretch(0)
        inner_layout.addLayout(center_row)
        inner_layout.addStretch(1)

        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._build_banner(root)

    def _build_banner(self, root_layout):
        self.banner = QFrame()
        self.banner.setObjectName("warnBanner")
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(12, 6, 6, 6)
        banner_layout.setSpacing(8)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        banner_layout.addWidget(self.warning_label, 1)

        self.dismiss_btn = QToolButton()
        self.dismiss_btn.setText("✕")
        self.dismiss_btn.setCursor(Qt.PointingHandCursor)
        self.dismiss_btn.clicked.connect(self.dismiss_warning)
        self.dismiss_btn.setAutoRaise(True)
        banner_layout.addWidget(self.dismiss_btn)

        root_layout.addWidget(self.banner)
        if self._settings.value(self.WARNING_DISMISSED_KEY, False, type=bool):
            self.banner.setVisible(False)

    # ── 自适应列数 ──────────────────────────────────────

    def _columns_per_group(self) -> int:
        """宽屏时每组 2 列，窄屏 1 列（默认窗口就是现在的单列布局）。"""
        effective = min(max(self.width() - 2 * PAGE_MARGIN, 0), CONTENT_MAX_WIDTH)
        per_group = (effective - GROUP_GAP) / 2
        return 2 if per_group >= 2 * CARD_MIN_WIDTH + GRID_GAP else 1

    def _update_grid(self):
        columns = self._columns_per_group()
        if columns == self._grid_columns:
            return
        self._grid_columns = columns
        for grid, group in self._grids:
            while grid.count():
                grid.takeAt(0)               # 只取出，卡片对象复用
            for index, feat in enumerate(group["features"]):
                grid.addWidget(self._cards[feat["id"]], index // columns, index % columns)
            for col in range(2):
                grid.setColumnStretch(col, 1 if col < columns else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_grid()

    # ── 文案与样式 ──────────────────────────────────────

    def _apply_lang(self):
        for lbl, key in self._section_labels:
            lbl.setText(self._lang.tr(key))
        self.warning_label.setText(self._lang.tr("home.warning"))
        self.dismiss_btn.setToolTip(self._lang.tr("home.warning.dismiss"))
        self.dismiss_btn.setAccessibleName(self._lang.tr("home.warning.dismiss"))

    def _apply_style(self):
        c = self._theme.current_colors
        for lbl, _ in self._section_labels:
            lbl.setStyleSheet(
                f"font-size: 10.5pt; font-weight: bold; color: {c['PRIMARY']}; padding: 2px 0;")
        self.banner.setStyleSheet(
            f"QFrame#warnBanner {{ background-color: {c['WARNING_BG']}; "
            f"border: 1px solid {c['WARNING_BORDER']}; border-radius: 6px; }}")
        self.warning_label.setStyleSheet(
            f"font-size: 9.5pt; color: {c['WARNING_TEXT']}; background: transparent; border: none;")
        self.dismiss_btn.setStyleSheet(
            f"QToolButton {{ color: {c['WARNING_TEXT']}; background: transparent; "
            f"border: none; font-size: 11pt; padding: 0 4px; }} "
            f"QToolButton:hover {{ color: {c['TEXT_PRIMARY']}; }}")

    def dismiss_warning(self):
        """收起注意事项，并记住已读（写入 QSettings）。"""
        self.banner.setVisible(False)
        self._settings.setValue(self.WARNING_DISMISSED_KEY, True)

    def _on_theme_changed(self, _theme_name: str):
        self._apply_style()

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()
