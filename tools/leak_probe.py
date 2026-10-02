"""Quantify resource growth per repeated operation.

Rebuilding a menu or a worker should not accumulate objects, and an abandoned or
failed streaming export must not leave openpyxl temp files behind. Measured:

  * preset menus rebuilt on every theme change (``_apply_styles``)
  * the field-distribution menu rebuilt on every column change
  * worker recycling after a finished QThread
  * %TEMP%/openpyxl.* leftovers after "no output needed" and after a failed export

Usage:  python tools/leak_probe.py
"""
import gc
import glob
import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import bench_common as bc  # noqa: E402

if "--core-dir" in os.sys.argv:
    _core_dir = os.sys.argv[os.sys.argv.index("--core-dir") + 1]
    if not os.path.isabs(_core_dir):
        _core_dir = os.path.join(bc.ROOT, _core_dir)
    os.sys.path.insert(0, _core_dir)
    print(f"core modules from: {_core_dir}")

from PySide6.QtCore import QEvent, QCoreApplication, QSettings, QThread  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu  # noqa: E402

REPEATS = 10


def flush(app) -> None:
    """Deliver deferred deletes (a running event loop does this for us)."""
    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def menu_count(widget) -> int:
    return len(widget.findChildren(QMenu))


def openpyxl_temp_files() -> set:
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "openpyxl.*")))


def _make_unique_fixture(path: str) -> str:
    """小表，去重列上没有任何重复值。"""
    if not os.path.exists(path):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["编号", "名称"])
        for i in range(500):
            ws.append([f"ID{i:04d}", f"名称{i}"])
        wb.save(path)
        wb.close()
    return path


def _make_broken_csv(path: str) -> str:
    """非 UTF-8 的 CSV：转换必然在读取中途失败。"""
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write("列A,列B\n".encode("gbk"))
            fh.write(b"\xff\xfe\x00\x81bad-bytes\n" * 2000)
    return path


def temp_file_check(app) -> tuple:
    """放弃输出 / 转换失败两条路径都不应留下 openpyxl 临时文件。"""
    from core.converter import ConvertWorker
    from core.deduper import DedupWorker

    work_dir = os.path.join(bc.ROOT, "test_output", "leakprobe")
    os.makedirs(work_dir, exist_ok=True)
    unique_xlsx = _make_unique_fixture(os.path.join(work_dir, "unique.xlsx"))
    broken_csv = _make_broken_csv(os.path.join(work_dir, "broken.csv"))

    before = openpyxl_temp_files()

    dedup = DedupWorker()
    dedup.configure(file_path=unique_xlsx, sheet_name="Sheet", columns=["编号"],
                    keep="first", output_dir=work_dir)
    dedup.run()
    flush(app)

    convert = ConvertWorker()
    convert.configure(file_paths=[broken_csv], target_format="xlsx", output_dir=work_dir)
    convert.run()
    flush(app)
    gc.collect()

    leftover = openpyxl_temp_files() - before
    no_output = not os.path.exists(os.path.join(work_dir, "unique_去重结果.xlsx"))
    return leftover, no_output


def main():
    app = QApplication([])

    from app.features.split import SplitFeature
    try:
        from app.widgets.common import release_worker
    except ImportError:      # pre-change tree: no worker recycling helper
        release_worker = None

    settings = QSettings("GridFlow", "GridFlow")
    saved_theme = settings.value("theme", "light")

    feature = SplitFeature()
    feature._apply_styles()
    flush(app)
    base = menu_count(feature)

    for _ in range(REPEATS):
        feature._apply_styles()          # 主题切换时走的路径
        flush(app)
    after_styles = menu_count(feature)

    step2 = feature.step2
    values = {f"区域{i:02d}": 100 - i for i in range(12)}
    for _ in range(REPEATS):
        step2._build_field_menu(values)  # 每次换列都走这里
        flush(app)
    after_fields = menu_count(feature)

    # worker lifecycle: a finished QThread must be recycled, not accumulated
    class _DummyWorker(QThread):
        def run(self):
            pass

    worker_released = None
    if release_worker is not None:
        owner = type("Owner", (), {})()
        worker = _DummyWorker()
        worker.start()
        worker.wait(3000)
        owner._worker = worker
        release_worker(owner)
        flush(app)
        gc.collect()
        try:
            worker.isFinished()
            worker_released = False
        except RuntimeError:
            worker_released = True

    leftovers, no_output = temp_file_check(app)

    settings.setValue("theme", saved_theme)
    settings.sync()
    feature.deleteLater()
    flush(app)

    print(f"QMenu children: initial={base} "
          f"after {REPEATS} style passes={after_styles} "
          f"after {REPEATS} field-menu rebuilds={after_fields}")
    print(f"worker released after release_worker(): {worker_released}")
    print(f"openpyxl temp files left by abandoned/failed exports: {len(leftovers)}")
    print(f"'no duplicates' produced no output file: {no_output}")

    # base counts the two preset menus; the field menu stays attached (+1)
    ok = (after_styles <= base and after_fields <= base + 1
          and worker_released is not False
          and not leftovers and no_output)
    print("RESULT:", "no growth" if ok else "GROWTH DETECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
