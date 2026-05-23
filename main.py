import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.main_window import MainWindow
from app.features.split import SplitFeature
from app.features.merge import MergeFeature
from app.features.dedup import DedupFeature
from app.features.convert import ConvertFeature
from app.features.filter import FilterFeature


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GridFlow")
    app.setOrganizationName("GridFlow")

    base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
    icon_ext = "ico" if sys.platform == "win32" else "png"
    icon_path = os.path.join(base, "resources", f"icon.{icon_ext}")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.register_feature("split", SplitFeature())
    window.register_feature("merge", MergeFeature())
    window.register_feature("dedup", DedupFeature())
    window.register_feature("convert", ConvertFeature())
    window.register_feature("filter", FilterFeature())
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
