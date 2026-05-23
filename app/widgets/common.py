"""共享 UI 组件与样式"""
from PySide6.QtWidgets import QLabel, QToolButton, QMenu, QLineEdit

from app.theme import LIGHT_COLORS


def get_combo_style(c: dict = None) -> str:
    """下拉框统一样式"""
    if c is None:
        c = LIGHT_COLORS
    return (
        "QComboBox {"
        f"  background-color: {'#FFFFFF' if c == LIGHT_COLORS else '#334155'};"
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
        f"  background-color: {'#FFFFFF' if c == LIGHT_COLORS else '#1E293B'};"
        f"  border: 1px solid {c['BORDER']};"
        "  border-radius: 4px;"
        f"  color: {c['TEXT_PRIMARY']};"
        "  selection-background-color: #DBEAFE;"
        f"  selection-color: {c['TEXT_PRIMARY']};"
        "  outline: none;"
        "  padding: 2px;"
        "}"
        "QComboBox QAbstractItemView::item {"
        "  padding: 5px 12px;"
        "  min-height: 24px;"
        "}"
        "QComboBox QAbstractItemView::item:hover {"
        "  background-color: #EFF6FF;"
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
    button.setMenu(menu)


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
