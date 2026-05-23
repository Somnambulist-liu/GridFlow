"""全局 QSS 样式表"""


def build_global_stylesheet(c: dict) -> str:
    """Build the global QSS stylesheet from a color dictionary."""
    return f"""
/* ===== 全局 ===== */
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 10pt;
    color: {c["TEXT_PRIMARY"]};
}}

QMainWindow {{
    background-color: {c["BG_MAIN"]};
}}

/* ===== 卡片容器 ===== */
QFrame#card {{
    background-color: {c["BG_CARD"]};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_MD"]}px;
    padding: 12px;
}}

/* ===== 按钮 ===== */
QPushButton {{
    background-color: {c["BG_CARD"]};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_SM"]}px;
    padding: 6px 16px;
    min-height: 24px;
    color: {c["TEXT_PRIMARY"]};
}}
QPushButton:hover {{
    border-color: {c["PRIMARY"]};
    color: {c["PRIMARY"]};
}}
QPushButton:pressed {{
    background-color: {c["PRIMARY_LIGHT"]};
}}

QPushButton#primaryBtn {{
    background-color: {c["PRIMARY"]};
    color: white;
    border: none;
    font-size: 11pt;
    font-weight: bold;
    padding: 8px 32px;
    border-radius: {c["RADIUS_SM"]}px;
}}
QPushButton#primaryBtn:hover {{
    background-color: {c["PRIMARY_HOVER"]};
}}
QPushButton#primaryBtn:pressed {{
    background-color: #1E40AF;
}}
QPushButton#primaryBtn:disabled {{
    background-color: {c["TEXT_MUTED"]};
}}

QPushButton#successBtn {{
    background-color: {c["SUCCESS"]};
    color: white;
    border: none;
    padding: 6px 16px;
    border-radius: {c["RADIUS_SM"]}px;
}}
QPushButton#successBtn:hover {{
    background-color: #15803D;
}}

/* ===== 输入框 ===== */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {c["BG_INPUT"]};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_SM"]}px;
    padding: 6px 10px;
    min-height: 20px;
    color: {c["TEXT_PRIMARY"]};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {c["BORDER_FOCUS"]};
    background-color: {"#FFFFFF" if c == LIGHT_COLORS else "#334155"};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {"#FFFFFF" if c == LIGHT_COLORS else "#1E293B"};
    border: 1px solid {c["BORDER"]};
    color: {c["TEXT_PRIMARY"]};
    selection-background-color: {"#DBEAFE" if c == LIGHT_COLORS else "#1E3A5F"};
    selection-color: {c["TEXT_PRIMARY"]};
    outline: none;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 14px;
    min-height: 24px;
    color: {c["TEXT_PRIMARY"]};
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {"#EFF6FF" if c == LIGHT_COLORS else "#1E3A5F"};
}}

/* ===== 单选按钮 ===== */
QRadioButton {{
    spacing: 6px;
    color: {c["TEXT_PRIMARY"]};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {c["BORDER"]};
    border-radius: 10px;
}}
QRadioButton::indicator:checked {{
    border-color: {c["PRIMARY"]};
    background-color: {c["PRIMARY"]};
}}

/* ===== 复选框 ===== */
QCheckBox {{
    spacing: 6px;
    color: {c["TEXT_PRIMARY"]};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {c["BORDER"]};
    border-radius: {c["RADIUS_SM"]}px;
}}
QCheckBox::indicator:checked {{
    border-color: {c["PRIMARY"]};
    background-color: {c["PRIMARY"]};
}}

/* ===== 进度条 ===== */
QProgressBar {{
    background-color: {c["BG_INPUT"]};
    border: none;
    border-radius: {c["RADIUS_SM"]}px;
    height: 20px;
    text-align: center;
    color: {c["TEXT_PRIMARY"]};
}}
QProgressBar::chunk {{
    background-color: {c["PRIMARY"]};
    border-radius: {c["RADIUS_SM"]}px;
}}

/* ===== 表格 ===== */
QTableView {{
    background-color: {"#FFFFFF" if c == LIGHT_COLORS else "#1E293B"};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_SM"]}px;
    gridline-color: {c["BORDER"]};
    selection-background-color: {c["PRIMARY_LIGHT"]};
    selection-color: {c["TEXT_PRIMARY"]};
    outline: none;
}}
QTableView QHeaderView::section {{
    background-color: {c["BG_INPUT"]};
    border: none;
    border-right: 1px solid {c["BORDER"]};
    border-bottom: 1px solid {c["BORDER"]};
    padding: 6px 10px;
    font-weight: bold;
    color: {c["TEXT_SECONDARY"]};
}}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background-color: {c["BG_MAIN"]};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {c["TEXT_MUTED"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {c["TEXT_SECONDARY"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ===== 分割线 ===== */
QFrame#separator {{
    background-color: {c["BORDER"]};
    max-height: 1px;
}}

/* ===== 标签 ===== */
QLabel#title {{
    font-size: 14pt;
    font-weight: bold;
    color: {c["TEXT_PRIMARY"]};
}}
QLabel#subtitle {{
    font-size: 9pt;
    color: {c["TEXT_MUTED"]};
}}
QLabel#statValue {{
    font-size: 16pt;
    font-weight: bold;
    color: {c["PRIMARY"]};
}}
QLabel#statLabel {{
    font-size: 9pt;
    color: {c["TEXT_MUTED"]};
}}

/* ===== 拖拽区域 ===== */
QFrame#dropZone {{
    background-color: {c["BG_INPUT"]};
    border: 2px dashed {c["BORDER"]};
    border-radius: {c["RADIUS_LG"]}px;
    min-height: 80px;
}}
QFrame#dropZone:hover {{
    border-color: {c["PRIMARY"]};
    background-color: {c["PRIMARY_LIGHT"]};
}}

/* ===== 工具提示 ===== */
QToolTip {{
    background-color: {c["TEXT_PRIMARY"]};
    color: {"white" if c == LIGHT_COLORS else "#0F172A"};
    border: none;
    border-radius: {c["RADIUS_SM"]}px;
    padding: 4px 8px;
}}
"""


# Backward compatibility: module-level GLOBAL_STYLESHEET for existing code
from app.theme import LIGHT_COLORS

GLOBAL_STYLESHEET = build_global_stylesheet(LIGHT_COLORS)
