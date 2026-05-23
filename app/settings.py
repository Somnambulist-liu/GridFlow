"""App settings via QSettings"""
from PySide6.QtCore import QSettings

_settings = QSettings("GridFlow", "GridFlow")


def get_last_dir(feature_id: str) -> str:
    return _settings.value(f"last_dir/{feature_id}", "")


def set_last_dir(feature_id: str, path: str):
    import os
    if os.path.isfile(path):
        path = os.path.dirname(path)
    _settings.setValue(f"last_dir/{feature_id}", path)
