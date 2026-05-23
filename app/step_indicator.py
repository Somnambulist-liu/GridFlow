from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from app.theme_manager import ThemeManager
from app.i18n import LangManager


class StepIndicator(QFrame):
    step_clicked = Signal(int)  # step index (0-based)

    STEP_KEYS = ["split.step1", "split.step2", "split.step3"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self._current = 0
        self._theme = ThemeManager.instance()
        self._lang = LangManager.instance()
        self._step_widgets = []
        self._setup_ui()
        self._apply_lang()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._lang.lang_changed.connect(self._on_lang_changed)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 8, 40, 8)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        self._step_widgets = []
        self._circle_labels = []
        self._line_frames = []

        for i, key in enumerate(self.STEP_KEYS):
            if i > 0:
                line = QFrame()
                line.setFixedSize(60, 2)
                line.setObjectName(f"stepLine{i}")
                layout.addWidget(line)
                self._step_widgets.append(("line", line))
                self._line_frames.append(line)

            step_widget = self._make_step(i + 1, "")
            layout.addWidget(step_widget)
            self._step_widgets.append(("step", step_widget))

        self._apply_theme()

    def _make_step(self, num: int, name: str) -> QWidget:
        widget = QWidget()
        widget.setFixedSize(100, 56)
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        vbox.setAlignment(Qt.AlignCenter)

        circle = QLabel(str(num))
        circle.setFixedSize(32, 32)
        circle.setAlignment(Qt.AlignCenter)
        circle.setObjectName(f"circle{num}")
        vbox.addWidget(circle, alignment=Qt.AlignCenter)

        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName(f"label{num}")
        vbox.addWidget(label, alignment=Qt.AlignCenter)

        widget.circle = circle
        widget.label = label
        return widget

    def _apply_lang(self):
        for item_type, widget in self._step_widgets:
            if item_type == "step":
                step_num = int(widget.circle.objectName().replace("circle", ""))
                key = self.STEP_KEYS[step_num - 1]
                widget.label.setText(self._lang.tr(key))

    def _on_lang_changed(self, _lang: str):
        self._apply_lang()

    def _apply_theme(self):
        c = self._theme.current_colors
        for item_type, widget in self._step_widgets:
            if item_type == "step":
                self._refresh_step_widget(widget, c)
            elif item_type == "line":
                self._refresh_line(widget, c)

    def _refresh_step_widget(self, widget, c):
        step_num = int(widget.circle.objectName().replace("circle", ""))
        if step_num < self._current + 1:
            widget.circle.setStyleSheet(
                f"background-color: {c['SUCCESS']}; color: white; border-radius: 16px; "
                "font-size: 13pt; font-weight: bold;")
            widget.label.setStyleSheet(f"color: {c['SUCCESS']}; font-size: 9pt; font-weight: bold;")
        elif step_num == self._current + 1:
            widget.circle.setStyleSheet(
                f"background-color: {c['PRIMARY']}; color: white; border-radius: 16px; "
                "font-size: 14pt; font-weight: bold;")
            widget.label.setStyleSheet(f"color: {c['PRIMARY']}; font-size: 9pt; font-weight: bold;")
        else:
            widget.circle.setStyleSheet(
                f"background-color: {c['TEXT_MUTED']}; color: white; border-radius: 16px; "
                "font-size: 13pt; font-weight: bold;")
            widget.label.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 9pt;")

    def _refresh_line(self, widget, c):
        line_num = int(widget.objectName().replace("stepLine", ""))
        if line_num <= self._current:
            widget.setStyleSheet(f"background-color: {c['SUCCESS']}; border-radius: 1px;")
        else:
            widget.setStyleSheet(f"background-color: {c['TEXT_MUTED']}; border-radius: 1px;")

    def set_current(self, index: int):
        self._current = index
        self._apply_theme()

    def _on_theme_changed(self, _theme_name: str):
        self._apply_theme()
