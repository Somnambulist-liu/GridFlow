import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Excel 分表拆分工具")
    app.setOrganizationName("Sheet2Split")

    base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
    icon_path = os.path.join(base, "resources", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
