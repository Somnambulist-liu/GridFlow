"""共享 UI 组件与样式"""
from PySide6.QtWidgets import QLabel, QToolButton, QMenu, QLineEdit, QFrame
from PySide6.QtCore import Signal, Qt

from app.theme import LIGHT_COLORS


class ClickableFrame(QFrame):
    """整块可点击的卡片/拖拽区（QFrame 本身没有 clicked 信号）。"""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def checkbox_style(c: dict, size: int = 15, color_key: str = "TEXT_SECONDARY",
                   font_size: str = "9pt") -> str:
    """复选框样式：选中只打勾（勾用主色），不填底色。

    功能页里各自写死的 indicator 样式会让“已勾选”只剩一个色块，这里统一走
    resources/check*.png，并保留 hover / disabled 反馈。
    """
    from app.resources import qss_url

    tick = qss_url("check.png" if c == LIGHT_COLORS else "check_dark.png")
    return (
        f"QCheckBox {{ color: {c[color_key]}; font-size: {font_size}; spacing: 6px; }} "
        f"QCheckBox:disabled {{ color: {c['TEXT_MUTED']}; }} "
        f"QCheckBox::indicator {{ width: {size}px; height: {size}px; border-radius: 3px; "
        f"border: 1px solid {c['BORDER']}; background-color: {c['BG_INPUT']}; }} "
        f"QCheckBox::indicator:hover {{ border-color: {c['PRIMARY']}; }} "
        f"QCheckBox::indicator:checked {{ background-color: transparent; "
        f"border: none; image: {tick}; }} "
        f"QCheckBox::indicator:disabled {{ background-color: {c['BG_MAIN']}; }} "
        f"QCheckBox::indicator:checked:disabled {{ background-color: transparent; "
        f"border: none; }} "
    )


def set_button_menu(button: QToolButton, menu: QMenu) -> None:
    """给按钮挂菜单，同时释放旧的菜单。

    QToolButton.setMenu() 不会销毁旧菜单，而旧菜单以按钮为父对象，会一直挂在
    控件树上；主题切换/换列时反复建菜单就会持续累积。这里先脱离父对象（立刻从
    控件树消失），再交给事件循环回收。
    """
    previous = button.menu()
    button.setMenu(menu)
    if previous is not None and previous is not menu:
        previous.hide()
        previous.setParent(None)
        previous.deleteLater()


def release_worker(owner) -> None:
    """释放上一次运行结束的 QThread worker。

    各功能页每执行一次都会 ``self._worker = XWorker(self)``，旧 worker 以页面为
    父对象，若不回收就会随操作次数累积（线程对象 + 信号连接 + 配置字符串）。
    """
    worker = getattr(owner, "_worker", None)
    if worker is None:
        return
    if worker.isFinished():
        worker.deleteLater()
        owner._worker = None


def get_combo_style(c: dict = None) -> str:
    """下拉框统一样式"""
    if c is None:
        c = LIGHT_COLORS
    return (
        "QComboBox {"
        f"  background-color: {c['BG_CARD'] if c == LIGHT_COLORS else c['BG_INPUT']};"
        f"  border: 1px solid {c['BORDER']};"
        f"  border-radius: {c['RADIUS_SM']}px;"
        f"  padding: 6px 10px;"
        f"  color: {c['TEXT_PRIMARY']};"
        "}"
        "QComboBox:hover {"
        f"  border-color: {c['PRIMARY']};"
        "}"
        "QComboBox::drop-down {"
        "  border: none;"
        "  padding-right: 6px;"
        "}"
        "QComboBox QAbstractItemView {"
        f"  background-color: {c['BG_CARD']};"
        f"  border: 1px solid {c['BORDER']};"
        "  border-radius: 4px;"
        f"  color: {c['TEXT_PRIMARY']};"
        f"  selection-background-color: {c['PRIMARY_LIGHT']};"
        f"  selection-color: {c['TEXT_PRIMARY']};"
        "  outline: none;"
        "  padding: 2px;"
        "}"
        "QComboBox QAbstractItemView::item {"
        "  padding: 5px 12px;"
        "  min-height: 24px;"
        "}"
        "QComboBox QAbstractItemView::item:hover {"
        f"  background-color: {c['PRIMARY_LIGHT_HOVER']};"
        "}"
    )


# Backward-compatible module-level alias
COMBO_STYLE = get_combo_style(LIGHT_COLORS)


def setup_preset_menu(button: QToolButton, target: QLineEdit, presets: list,
                      c: dict = None):
    """为下拉按钮设置预设选项菜单"""
    if c is None:
        c = LIGHT_COLORS
    menu = QMenu(button)
    menu.setStyleSheet(
        f"QMenu {{ background-color: {'white' if c == LIGHT_COLORS else '#1E293B'}; "
        f"border: 1px solid {'#E2E8F0' if c == LIGHT_COLORS else '#334155'}; "
        f"border-radius: 6px; padding: 4px; }} "
        f"QMenu::item {{ padding: 5px 16px; border-radius: 3px; color: {c['TEXT_PRIMARY']}; }} "
        f"QMenu::item:selected {{ background-color: {'#DBEAFE' if c == LIGHT_COLORS else '#1E3A5F'}; "
        f"color: {c['TEXT_PRIMARY']}; }}"
    )
    for label_text, value in presets:
        action = menu.addAction(label_text)
        action.triggered.connect(lambda checked, v=value: target.setText(v))
    set_button_menu(button, menu)


def section_label(text: str, c: dict = None) -> QLabel:
    """分区标题标签"""
    if c is None:
        c = LIGHT_COLORS
    label = QLabel(text)
    label.setStyleSheet(
        f"font-size: 9pt; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-bottom: 2px;"
    )
    return label


def make_drop_btn(c: dict = None) -> QToolButton:
    """创建带下拉菜单的小按钮"""
    if c is None:
        c = LIGHT_COLORS
    btn = QToolButton()
    btn.setText("▼")
    btn.setPopupMode(QToolButton.InstantPopup)
    btn.setFixedWidth(20)
    btn.setStyleSheet(
        f"QToolButton {{ color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; "
        f"border-radius: 0 4px 4px 0; background: {c['BG_INPUT']}; font-size: 7pt; }} "
        f"QToolButton:hover {{ background: {c['PRIMARY_LIGHT']}; }} "
        "QToolButton::menu-indicator { image: none; }"
    )
    return btn
