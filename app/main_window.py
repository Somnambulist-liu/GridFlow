import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.styles import GLOBAL_STYLESHEET
from app.theme import PRIMARY, PRIMARY_HOVER, TEXT_MUTED, BORDER, RADIUS_SM, BG_CARD, TEXT_SECONDARY
from app.step_indicator import StepIndicator
from app.wizard_steps import Step1File, Step2Config, Step3Execute
from core.splitter import SplitWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excel 分表拆分工具")
        base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
        icon_path = os.path.join(base, "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(640, 580)
        self.resize(700, 620)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        self._worker: SplitWorker | None = None
        self._current_step = 0
        self._current_preview_data = {}

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 头部：标题 + 步骤条 ──
        header = QWidget()
        header.setStyleSheet(f"background-color: {BG_CARD}; border-bottom: 1px solid {BORDER};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 10, 0, 2)
        header_layout.setSpacing(4)

        title = QLabel("\U0001F4CA Excel 分表拆分工具")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1E293B;")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)

        self.step_indicator = StepIndicator()
        header_layout.addWidget(self.step_indicator)

        root.addWidget(header)

        # ── 步骤内容区 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: transparent;")

        self.step1 = Step1File()
        self.step2 = Step2Config()
        self.step3 = Step3Execute()

        self.stack.addWidget(self.step1)
        self.stack.addWidget(self.step2)
        self.stack.addWidget(self.step3)
        root.addWidget(self.stack, 1)

        # ── 底部导航栏 ──
        footer = QWidget()
        footer.setStyleSheet(f"background-color: {BG_CARD}; border-top: 1px solid {BORDER};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        self.back_btn = QPushButton("←  上一步")
        self.back_btn.setStyleSheet(self._nav_btn_style())
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_prev)
        footer_layout.addWidget(self.back_btn)

        footer_layout.addStretch()

        self.next_btn = QPushButton("下一步  →")
        self.next_btn.setStyleSheet(self._nav_btn_style(primary=True))
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._go_next)
        footer_layout.addWidget(self.next_btn)

        root.addWidget(footer)

        # 初始状态
        self.stack.setCurrentIndex(0)

    def _nav_btn_style(self, primary: bool = False) -> str:
        if primary:
            return (
                f"QPushButton {{ background-color: {PRIMARY}; color: white; border: none; "
                f"border-radius: {RADIUS_SM}px; padding: 8px 24px; font-size: 11pt; font-weight: bold; }} "
                f"QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }} "
                f"QPushButton:disabled {{ background-color: {TEXT_MUTED}; }}"
            )
        return (
            f"QPushButton {{ background-color: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px; padding: 8px 20px; font-size: 11pt; }} "
            f"QPushButton:hover {{ color: #1E293B; border-color: {TEXT_MUTED}; }}"
        )

    def _connect_signals(self):
        # Step 1 → load file → Step 2
        self.step1.file_selected.connect(self._on_file_loaded)

        # Step 2 → config valid → enable next
        self.step2.config_valid.connect(self._on_config_valid)

        # Step 2 → column loaded → Step 3 preview
        self.step2.column_loaded.connect(self._on_preview_update)

        # Step 3 → start split
        self.step3.start_requested.connect(self._start_split)

    # ── Navigation ─────────────────────────────────────────
    def _go_next(self):
        if self._current_step == 0:
            self._navigate_to(1)
        elif self._current_step == 1:
            self._navigate_to(2)

    def _go_prev(self):
        if self._current_step > 0:
            self._navigate_to(self._current_step - 1)

    def _navigate_to(self, step: int):
        self._current_step = step
        self.stack.setCurrentIndex(step)
        self.step_indicator.set_current(step)

        self.back_btn.setVisible(step > 0)
        self.next_btn.setVisible(step < 2)

        if step == 0:
            self.next_btn.setText("下一步  →")
            self.next_btn.setEnabled(bool(self.step1.file_path))
        elif step == 1:
            self.next_btn.setText("下一步  →")
            self.next_btn.setEnabled(self.step2.is_valid())
        elif step == 2:
            self.next_btn.setVisible(False)
            mode = self.step2.get_config()["mode"]
            self.step3.set_mode(mode)

    # ── Step Callbacks ─────────────────────────────────────
    def _on_file_loaded(self, file_path: str, sheets: list):
        self.next_btn.setEnabled(True)
        self.step2.load_file(file_path, sheets)

    def _on_config_valid(self, valid: bool):
        if self._current_step == 1:
            self.next_btn.setEnabled(valid)

    def _on_preview_update(self, column_name: str, value_counts: dict):
        self._current_preview_data = value_counts
        mode = self.step2.get_config()["mode"]
        self.step3.set_mode(mode)
        self.step3.update_preview(column_name, value_counts)
        self.step3.set_ready(True)

    # ── Split Logic ────────────────────────────────────────
    def _start_split(self):
        config = self.step2.get_config()
        if not config["file_path"]:
            return

        if config["mode"] == "sheets":
            output_path = os.path.join(
                config["output_dir"],
                f"{os.path.splitext(os.path.basename(config['file_path']))[0]}_拆分结果.xlsx"
            )
        else:
            output_path = ""

        self._worker = SplitWorker(self)
        self._worker.configure(
            file_path=config["file_path"],
            sheet_name=config["sheet_name"],
            column=config["column"],
            mode=config["mode"],
            output_dir=config["output_dir"],
            output_path=output_path,
            name_pattern=config["name_pattern"],
            keep_header=config["keep_header"],
        )

        self._worker.progress.connect(self.step3.update_progress)
        self._worker.finished.connect(self._on_split_finished)
        self._worker.error_occurred.connect(self._on_split_error)
        self._worker.start()

    def _on_split_finished(self, summary: str):
        config = self.step2.get_config()
        self.step3.show_result_stats(config["output_dir"])
        self.step3.on_finished(summary)

    def _on_split_error(self, error_msg: str):
        self.step3.on_error(error_msg)
