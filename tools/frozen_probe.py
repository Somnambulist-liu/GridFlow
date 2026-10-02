"""Console entry point used to verify a frozen build can lazily import features.

A PyInstaller build cannot see ``import_module("app.features.split")``, so this
probe is frozen with the same hidden imports as the real app and then walks the
exact path a click takes: build every feature page through the factory in
``main.FEATURE_MODULES``. It prints ``FROZEN_OK`` on success.

    pyinstaller --noconfirm --console --onefile --name GridFlowProbe \
        --distpath dist_probe --workpath build_probe --paths . \
        --hidden-import app.updater --hidden-import app.settings \
        --hidden-import app.settings_dialog \
        --hidden-import app.features.split ... tools/frozen_probe.py
    dist_probe/GridFlowProbe.exe
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    from PySide6.QtWidgets import QApplication

    import main as app_main

    app = QApplication([])
    from app.main_window import MainWindow

    window = MainWindow()
    for feature_id, module_name, class_name in app_main.FEATURE_MODULES:
        widget = app_main._make_feature_factory(module_name, class_name)()
        got = type(widget).__name__
        if got != class_name:
            print(f"FROZEN_FAIL {feature_id}: {got} != {class_name}")
            return 1
        window.register_feature(feature_id, lambda w=widget: w)

    window.show()
    app.processEvents()

    # exercise dynamic imports that only happen on user action
    from app.settings_dialog import SettingsDialog  # noqa: F401
    from app.updater import UpdateChecker          # noqa: F401
    from app.settings import get_default_output_dir  # noqa: F401
    get_default_output_dir()

    window.close()
    print(f"FROZEN_OK frozen={getattr(sys, 'frozen', False)} "
          f"features={len(app_main.FEATURE_MODULES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
