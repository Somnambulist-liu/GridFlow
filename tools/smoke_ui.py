"""Headless UI smoke test for the lazily-created feature pages.

Checks that:
  * every registered feature can actually be opened (module import + widget build)
  * the page becomes the current stack widget and the back button appears
  * re-visiting a feature reuses the same widget (no duplicate construction)
  * registering an already-built QWidget still works (back-compat path)
  * theme / language switching after lazy creation does not raise

QSettings values touched here are restored afterwards.

Usage:  python tools/smoke_ui.py
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import bench_common as bc  # noqa: E402

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402


def main() -> int:
    app = QApplication([])
    import main as app_main  # noqa: F401  (module under test)
    from app.main_window import MainWindow

    settings = QSettings("GridFlow", "GridFlow")
    saved = {key: settings.value(key)
             for key in ("theme", "language")
             if settings.contains(key)}

    failures = []
    window = MainWindow()
    for feature_id, module_name, class_name in app_main.FEATURE_MODULES:
        window.register_feature(feature_id,
                                app_main._make_feature_factory(module_name, class_name))
    window.show()
    app.processEvents()

    if window.stack.count() != 1:
        failures.append(f"startup built {window.stack.count()} pages, expected 1 (home)")

    for feature_id, module_name, class_name in app_main.FEATURE_MODULES:
        t0 = time.perf_counter()
        window._on_feature_selected(feature_id)
        app.processEvents()
        elapsed = (time.perf_counter() - t0) * 1000
        widget = window._feature_widgets.get(feature_id)
        if widget is None:
            failures.append(f"{feature_id}: no widget created")
            continue
        if type(widget).__name__ != class_name:
            failures.append(f"{feature_id}: got {type(widget).__name__}, expected {class_name}")
        if window.stack.currentWidget() is not widget:
            failures.append(f"{feature_id}: not the current page")
        if not window.back_btn.isVisible():
            failures.append(f"{feature_id}: back button hidden")
        print(f"  {feature_id:<9} {type(widget).__name__:<16} first open {elapsed:7.1f} ms")

        # second visit must reuse the same instance
        window._on_feature_selected(feature_id)
        if window._feature_widgets[feature_id] is not widget:
            failures.append(f"{feature_id}: re-created on second visit")
        window._go_home()
        if window.stack.currentIndex() != 0:
            failures.append(f"{feature_id}: back home did not switch to index 0")
        window._on_feature_selected(feature_id)

    expected_pages = 1 + len(app_main.FEATURE_MODULES)
    if window.stack.count() != expected_pages:
        failures.append(f"stack has {window.stack.count()} pages, expected {expected_pages}")

    # back-compat: a pre-built widget can still be registered
    legacy = QLabel("legacy")
    window.register_feature("legacy", legacy)
    window._on_feature_selected("legacy")
    app.processEvents()
    if window.stack.currentWidget() is not legacy:
        failures.append("legacy widget registration broken")

    # theme + language switching after lazy creation
    try:
        window._theme.toggle()
        app.processEvents()
        window._lang.toggle()
        app.processEvents()
        window._lang.toggle()
        app.processEvents()
        window._theme.toggle()
        app.processEvents()
    except Exception as exc:  # pragma: no cover - reported as failure
        failures.append(f"theme/lang switch raised {type(exc).__name__}: {exc}")

    # restore persisted settings
    if "theme" in saved:
        settings.setValue("theme", saved["theme"])
    if "language" in saved:
        settings.setValue("language", saved["language"])
    settings.sync()

    window.close()
    app.processEvents()

    if failures:
        print("\nFAILED:")
        for item in failures:
            print("  -", item)
        return 1
    print("\nOK: all feature pages open lazily and behave correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
