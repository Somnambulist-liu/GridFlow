"""全局 QSS 样式表"""

from app.theme import (
    PRIMARY, PRIMARY_HOVER, PRIMARY_LIGHT,
    SUCCESS, SUCCESS_LIGHT,
    BG_MAIN, BG_CARD, BG_INPUT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER, BORDER_FOCUS,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)

GLOBAL_STYLESHEET = f"""
/* ===== 全局 ===== */
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 10pt;
    color: {TEXT_PRIMARY};
}}

QMainWindow {{
    background-color: {BG_MAIN};
}}

/* ===== 卡片容器 ===== */
QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
    padding: 12px;
}}

/* ===== 按钮 ===== */
QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 6px 16px;
    min-height: 24px;
    color: {TEXT_PRIMARY};
}}
QPushButton:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
}}
QPushButton:pressed {{
    background-color: {PRIMARY_LIGHT};
}}

QPushButton#primaryBtn {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    font-size: 11pt;
    font-weight: bold;
    padding: 8px 32px;
    border-radius: {RADIUS_SM}px;
}}
QPushButton#primaryBtn:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton#primaryBtn:pressed {{
    background-color: #1E40AF;
}}
QPushButton#primaryBtn:disabled {{
    background-color: {TEXT_MUTED};
}}

QPushButton#successBtn {{
    background-color: {SUCCESS};
    color: white;
    border: none;
    padding: 6px 16px;
    border-radius: {RADIUS_SM}px;
}}
QPushButton#successBtn:hover {{
    background-color: #15803D;
}}

/* ===== 输入框 ===== */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 6px 10px;
    min-height: 20px;
    color: {TEXT_PRIMARY};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {BORDER_FOCUS};
    background-color: white;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
    selection-background-color: #DBEAFE;
    selection-color: {TEXT_PRIMARY};
    outline: none;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 14px;
    min-height: 24px;
    color: {TEXT_PRIMARY};
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: #EFF6FF;
}}

/* ===== 单选按钮 ===== */
QRadioButton {{
    spacing: 6px;
    color: {TEXT_PRIMARY};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER};
    border-radius: 10px;
}}
QRadioButton::indicator:checked {{
    border-color: {PRIMARY};
    background-color: {PRIMARY};
}}

/* ===== 复选框 ===== */
QCheckBox {{
    spacing: 6px;
    color: {TEXT_PRIMARY};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER};
    border-radius: {RADIUS_SM}px;
}}
QCheckBox::indicator:checked {{
    border-color: {PRIMARY};
    background-color: {PRIMARY};
}}

/* ===== 进度条 ===== */
QProgressBar {{
    background-color: {BG_INPUT};
    border: none;
    border-radius: {RADIUS_SM}px;
    height: 20px;
    text-align: center;
    color: {TEXT_PRIMARY};
}}
QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: {RADIUS_SM}px;
}}

/* ===== 表格 ===== */
QTableView {{
    background-color: white;
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    gridline-color: {BORDER};
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {TEXT_PRIMARY};
    outline: none;
}}
QTableView QHeaderView::section {{
    background-color: {BG_INPUT};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background-color: {BG_MAIN};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {TEXT_MUTED};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_SECONDARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ===== 分割线 ===== */
QFrame#separator {{
    background-color: {BORDER};
    max-height: 1px;
}}

/* ===== 标签 ===== */
QLabel#title {{
    font-size: 14pt;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel#subtitle {{
    font-size: 9pt;
    color: {TEXT_MUTED};
}}
QLabel#statValue {{
    font-size: 16pt;
    font-weight: bold;
    color: {PRIMARY};
}}
QLabel#statLabel {{
    font-size: 9pt;
    color: {TEXT_MUTED};
}}

/* ===== 拖拽区域 ===== */
QFrame#dropZone {{
    background-color: {BG_INPUT};
    border: 2px dashed {BORDER};
    border-radius: {RADIUS_LG}px;
    min-height: 80px;
}}
QFrame#dropZone:hover {{
    border-color: {PRIMARY};
    background-color: {PRIMARY_LIGHT};
}}

/* ===== 工具提示 ===== */
QToolTip {{
    background-color: {TEXT_PRIMARY};
    color: white;
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: 4px 8px;
}}
"""
