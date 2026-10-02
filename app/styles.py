"""全局 QSS 样式表"""
from app.resources import qss_url
from app.theme import LIGHT_COLORS


def build_global_stylesheet(c: dict) -> str:
    """Build the global QSS stylesheet from a color dictionary."""
    # 选中态只用主色画勾，不填底色；勾的颜色随主题（浅/深各一个资源）
    check_icon = qss_url("check.png" if c == LIGHT_COLORS else "check_dark.png")
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

/* 对话框/弹窗也走主题：以前只定义了 QMainWindow 背景，暗色下 QDialog 仍是系统亮色，
   配合全局浅色文字会变成"白底浅字"（更新对话框、下载进度框就是这样） */
QDialog, QMessageBox, QProgressDialog {{
    background-color: {c["BG_CARD"]};
    color: {c["TEXT_PRIMARY"]};
}}

QDialog QLabel, QProgressDialog QLabel {{
    color: {c["TEXT_PRIMARY"]};
    background: transparent;
}}

/* 文本域/说明区 */
QTextEdit, QTextBrowser, QPlainTextEdit {{
    background-color: {c["BG_INPUT"]};
    color: {c["TEXT_PRIMARY"]};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_SM"]}px;
    padding: 6px 8px;
    selection-background-color: {c["PRIMARY_LIGHT"]};
    selection-color: {c["TEXT_PRIMARY"]};
}}

/* ===== 卡片容器 ===== */
QFrame#card {{
    background-color: {c["BG_CARD"]};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_MD"]}px;
    padding: 12px;
}}

/* 设置对话框里的分组卡片 */
QFrame#settingsCard {{
    background-color: {c["BG_MAIN"]};
    border: 1px solid {c["BORDER"]};
    border-radius: {c["RADIUS_MD"]}px;
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
    border-color: {c["PRIMARY"]};
}}
QPushButton:focus {{
    border: 2px solid {c["PRIMARY"]};
}}
QPushButton:disabled {{
    color: {c["TEXT_MUTED"]};
    border-color: {c["BORDER"]};
    background-color: {c["BG_MAIN"]};
}}
QToolButton:focus, QCheckBox:focus, QRadioButton:focus {{
    outline: none;
    border: 1px solid {c["PRIMARY"]};
}}

/* ===== 复选框 / 单选：选中态要有明确反馈（对勾 / 圆点），禁用态明显区分 ===== */
QCheckBox, QRadioButton {{
    color: {c["TEXT_PRIMARY"]};
    spacing: 8px;
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: {c["TEXT_MUTED"]};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {c["BORDER"]};
    background-color: {c["BG_INPUT"]};
}}
QCheckBox::indicator:hover {{
    border-color: {c["PRIMARY"]};
}}
/* 选中 = 只打勾，不填底色（勾用主色） */
QCheckBox::indicator:checked {{
    background-color: {c["BG_INPUT"]};
    border-color: {c["BORDER"]};
    image: {check_icon};
}}
QCheckBox::indicator:checked:hover {{
    border-color: {c["PRIMARY"]};
}}
QCheckBox::indicator:disabled {{
    background-color: {c["BG_MAIN"]};
    border-color: {c["BORDER"]};
}}
QCheckBox::indicator:checked:disabled {{
    background-color: {c["BG_MAIN"]};
    border-color: {c["TEXT_MUTED"]};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid {c["BORDER"]};
    background-color: {c["BG_INPUT"]};
}}
QRadioButton::indicator:hover {{
    border-color: {c["PRIMARY"]};
}}
/* 注意：:checked 里必须重写 border-radius，否则 Qt 会把圆角重置，
   16px 的指示器会画成“圆角方块”而不是圆点 */
QRadioButton::indicator:checked {{
    border: 2px solid {c["PRIMARY"]};
    border-radius: 8px;
    background-color: {c["PRIMARY"]};
}}
QRadioButton::indicator:disabled {{
    border-color: {c["TEXT_MUTED"]};
    background-color: {c["BG_MAIN"]};
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
    background-color: {c["PRIMARY_ACTIVE"]};
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
    background-color: {c["SUCCESS_HOVER"]};
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
    background-color: {c["BG_CARD"] if c == LIGHT_COLORS else c["BG_INPUT"]};
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

/* 单选 / 复选框样式统一在上面“复选框 / 单选”一节定义，这里不再重复，
   否则后面的规则会覆盖掉选中态的勾选反馈 */

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
