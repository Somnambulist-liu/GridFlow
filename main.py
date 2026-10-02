import sys
import os
from importlib import import_module

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 功能模块按需加载：启动时只建首页，点进某个功能才 import 对应模块
# （openpyxl 的导入约 200ms，之前每次启动都会付这个开销）
FEATURE_MODULES = (
    ("split", "app.features.split", "SplitFeature"),
    ("merge", "app.features.merge", "MergeFeature"),
    ("dedup", "app.features.dedup", "DedupFeature"),
    ("convert", "app.features.convert", "ConvertFeature"),
    ("filter", "app.features.filter", "FilterFeature"),
    ("columns", "app.features.columns", "ColumnsFeature"),
    ("pivot", "app.features.pivot", "PivotFeature"),
    ("validate", "app.features.validate", "ValidateFeature"),
)


def _make_feature_factory(module_name: str, class_name: str):
    """返回一个延迟构造功能页面的工厂。"""
    def factory():
        return getattr(import_module(module_name), class_name)()
    factory.__name__ = class_name
    return factory


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GridFlow")
    app.setOrganizationName("GridFlow")

    from app.resources import icon_path
    from app.main_window import MainWindow

    icon = icon_path()
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    window = MainWindow()
    for feature_id, module_name, class_name in FEATURE_MODULES:
        window.register_feature(feature_id, _make_feature_factory(module_name, class_name))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
