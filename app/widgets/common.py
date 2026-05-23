"""共享 UI 组件与样式"""
from PySide6.QtWidgets import QLabel, QToolButton, QMenu, QLineEdit

from app.theme import (
    PRIMARY, PRIMARY_LIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER, BG_INPUT, RADIUS_SM,
)

# 下拉框统一样式
COMBO_STYLE = (
    "QComboBox {"
    f"  background-color: #FFFFFF;"
    f"  border: 1px solid {BORDER};"
    f"  border-radius: {RADIUS_SM}px;"
    f"  padding: 6px 10px;"
    f"  color: {TEXT_PRIMARY};"
    "}"
    "QComboBox:hover {"
    f"  border-color: {PRIMARY};"
    "}"
    "QComboBox::drop-down {"
    "  border: none;"
    "  padding-right: 6px;"
    "}"
    "QComboBox QAbstractItemView {"
    "  background-color: #FFFFFF;"
    f"  border: 1px solid {BORDER};"
    f"  border-radius: 4px;"
    f"  color: {TEXT_PRIMARY};"
    "  selection-background-color: #DBEAFE;"
    f"  selection-color: {TEXT_PRIMARY};"
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


def setup_preset_menu(button: QToolButton, target: QLineEdit, presets: list):
    """为下拉按钮设置预设选项菜单"""
    menu = QMenu(button)
    menu.setStyleSheet(
        "QMenu { background-color: white; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px; } "
        "QMenu::item { padding: 5px 16px; border-radius: 3px; } "
        "QMenu::item:selected { background-color: #DBEAFE; color: #1E293B; }"
    )
    for label_text, value in presets:
        action = menu.addAction(label_text)
        action.triggered.connect(lambda checked, v=value: target.setText(v))
    button.setMenu(menu)


def section_label(text: str) -> QLabel:
    """分区标题标签"""
    label = QLabel(text)
    label.setStyleSheet(
        f"font-size: 9pt; font-weight: bold; color: {TEXT_SECONDARY}; margin-bottom: 2px;"
    )
    return label


def make_drop_btn() -> QToolButton:
    """创建带下拉菜单的小按钮"""
    btn = QToolButton()
    btn.setText("▼")
    btn.setPopupMode(QToolButton.InstantPopup)
    btn.setFixedWidth(20)
    btn.setStyleSheet(
        f"QToolButton {{ color: {TEXT_SECONDARY}; border: 1px solid {BORDER}; "
        f"border-radius: 0 4px 4px 0; background: {BG_INPUT}; font-size: 7pt; }} "
        f"QToolButton:hover {{ background: {PRIMARY_LIGHT}; }} "
        "QToolButton::menu-indicator { image: none; }"
    )
    return btn
