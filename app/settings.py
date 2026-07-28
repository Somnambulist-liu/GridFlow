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


def get_default_output_dir() -> str:
    return _settings.value("default_output_dir", "")


def set_default_output_dir(path: str):
    _settings.setValue("default_output_dir", path)


def get_auto_open_dir() -> bool:
    val = _settings.value("auto_open_dir", False)
    if isinstance(val, str):
        return val.lower() == "true"
    return bool(val)


def set_auto_open_dir(enabled: bool):
    _settings.setValue("auto_open_dir", enabled)


def get_auto_check_update() -> bool:
    val = _settings.value("auto_check_update", True)
    if isinstance(val, str):
        return val.lower() == "true"
    return bool(val)


def set_auto_check_update(enabled: bool):
    _settings.setValue("auto_check_update", enabled)


def get_ignored_version() -> str:
    return _settings.value("update/ignored_version", "") or ""


def set_ignored_version(version: str):
    _settings.setValue("update/ignored_version", version)
