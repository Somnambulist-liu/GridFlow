from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from app.theme import PRIMARY, PRIMARY_HOVER, SUCCESS, TEXT_MUTED, BG_CARD, BORDER


class StepIndicator(QFrame):
    step_clicked = Signal(int)  # step index (0-based)

    STEPS = ["选择文件", "拆分配置", "预览执行"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self._current = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 8, 40, 8)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        self._step_widgets = []
        for i, name in enumerate(self.STEPS):
            if i > 0:
                line = QFrame()
                line.setFixedSize(60, 2)
                line.setObjectName(f"stepLine{i}")
                line.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 1px;")
                layout.addWidget(line)
                self._step_widgets.append(("line", line))

            step_widget = self._make_step(i + 1, name)
            layout.addWidget(step_widget)
            self._step_widgets.append(("step", step_widget))

    def _make_step(self, num: int, name: str) -> QWidget:
        widget = QWidget()
        widget.setFixedSize(100, 56)
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        vbox.setAlignment(Qt.AlignCenter)

        self.circle_labels = getattr(self, '_circle_labels', [])
        circle = QLabel(str(num))
        circle.setFixedSize(32, 32)
        circle.setAlignment(Qt.AlignCenter)
        circle.setStyleSheet(
            f"background-color: {TEXT_MUTED}; color: white; border-radius: 16px; "
            "font-size: 13pt; font-weight: bold;"
        )
        circle.setObjectName(f"circle{num}")
        vbox.addWidget(circle, alignment=Qt.AlignCenter)

        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 9pt;")
        label.setObjectName(f"label{num}")
        vbox.addWidget(label, alignment=Qt.AlignCenter)

        widget.circle = circle
        widget.label = label
        return widget

    def set_current(self, index: int):
        self._current = index
        for item_type, widget in self._step_widgets:
            if item_type == "step":
                step_num = int(widget.circle.objectName().replace("circle", ""))
                if step_num <= index + 1:
                    widget.circle.setStyleSheet(
                        f"background-color: {SUCCESS}; color: white; border-radius: 16px; "
                        "font-size: 13pt; font-weight: bold;")
                    widget.label.setStyleSheet(f"color: {SUCCESS}; font-size: 9pt; font-weight: bold;")
                if step_num == index + 1:
                    widget.circle.setStyleSheet(
                        f"background-color: {PRIMARY}; color: white; border-radius: 16px; "
                        "font-size: 14pt; font-weight: bold;")
                    widget.label.setStyleSheet(f"color: {PRIMARY}; font-size: 9pt; font-weight: bold;")

        for item_type, widget in self._step_widgets:
            if item_type == "line":
                line_num = int(widget.objectName().replace("stepLine", ""))
                if line_num <= index:
                    widget.setStyleSheet(f"background-color: {SUCCESS}; border-radius: 1px;")
                else:
                    widget.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 1px;")
