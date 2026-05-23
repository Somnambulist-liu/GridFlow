"""Dynamic theme manager with light/dark mode support."""
from PySide6.QtCore import QObject, Signal, QSettings

from app.theme import LIGHT_COLORS, DARK_COLORS


class ThemeManager(QObject):
    theme_changed = Signal(str)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._settings = QSettings("GridFlow", "GridFlow")
        self._theme = self._settings.value("theme", "light")

    @property
    def theme(self):
        return self._theme

    @property
    def current_colors(self):
        return DARK_COLORS if self._theme == "dark" else LIGHT_COLORS

    def toggle(self):
        self._theme = "dark" if self._theme == "light" else "light"
        self._settings.setValue("theme", self._theme)
        self.theme_changed.emit(self._theme)
