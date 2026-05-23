"""Dynamic theme manager with light/dark/auto mode support."""
import subprocess
import sys
from PySide6.QtCore import QObject, Signal, QSettings, QTimer

from app.theme import LIGHT_COLORS, DARK_COLORS


def _detect_system_theme() -> str:
    """Detect OS-level dark/light preference. Returns 'dark' or 'light'."""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "dark" if value == 0 else "light"
        elif sys.platform == "darwin":
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True
            )
            return "dark" if "Dark" in result.stdout else "light"
        else:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True
            )
            return "dark" if "dark" in result.stdout.lower() else "light"
    except Exception:
        return "light"


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
        self._system_theme = _detect_system_theme()
        self._resolved = self._theme if self._theme != "auto" else self._system_theme

        # Poll system theme every 3 seconds when in auto mode
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_system_theme)
        if self._theme == "auto":
            self._poll_timer.start(3000)

    @property
    def theme(self):
        return self._theme

    @property
    def resolved_theme(self) -> str:
        return self._resolved

    @property
    def current_colors(self):
        return DARK_COLORS if self._resolved == "dark" else LIGHT_COLORS

    def toggle(self):
        """Cycle through light → dark → auto → light."""
        cycle = {"light": "dark", "dark": "auto", "auto": "light"}
        self._theme = cycle[self._theme]
        self._settings.setValue("theme", self._theme)
        self._update_resolved()
        self._poll_timer.start(3000) if self._theme == "auto" else self._poll_timer.stop()
        self.theme_changed.emit(self._theme)

    def _poll_system_theme(self):
        detected = _detect_system_theme()
        if detected != self._system_theme:
            self._system_theme = detected
            if self._theme == "auto":
                self._update_resolved()
                self.theme_changed.emit(self._theme)

    def _update_resolved(self):
        self._resolved = self._theme if self._theme != "auto" else self._system_theme
