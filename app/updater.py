"""Auto-update: check GitHub Releases, download, apply via batch script."""
import sys
import os
import json
import hashlib
import tempfile
import subprocess
import time
from http.client import HTTPSConnection
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextBrowser, QStackedWidget, QFrame, QWidget,
)

from app.resources import icon_path
from app.theme_manager import ThemeManager
from app.markdown_lite import to_html


REPO_OWNER = "Somnambulist-liu"
REPO_NAME = "GridFlow"
API_HOST = "api.github.com"
API_PATH = f"/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
CHECK_INTERVAL = 1800  # 30 minutes between auto-checks


# ── version helpers ─────────────────────────────────────────

def parse_version(tag: str) -> tuple:
    """Parse 'v3.4.0' or '3.4.0' → (3, 4, 0)."""
    t = tag.lstrip("vV")
    try:
        return tuple(int(x) for x in t.split("."))
    except Exception:
        return (0, 0, 0)


# ── helpers ─────────────────────────────────────────────────

def is_frozen() -> bool:
    return hasattr(sys, "_MEIPASS") or getattr(sys, "frozen", False)


def _http_get(host: str, path: str) -> dict | None:
    """Perform HTTPS GET and return parsed JSON, or None."""
    try:
        conn = HTTPSConnection(host, timeout=15)
        conn.request("GET", path, headers={
            "User-Agent": "GridFlow-Updater",
            "Accept": "application/vnd.github+json",
        })
        resp = conn.getresponse()
        if resp.status != 200:
            conn.close()
            return None
        data = json.loads(resp.read().decode())
        conn.close()
        return data
    except Exception:
        return None


# ── UpdateChecker ────────────────────────────────────────────

class UpdateChecker(QThread):
    """Background thread: checks GitHub API for latest release."""
    update_available = Signal(dict)   # {version, download_url, body, size}
    up_to_date = Signal()
    error_occurred = Signal(str)

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current_version = current_version

    def run(self):
        if not is_frozen():
            self.error_occurred.emit("not frozen")
            return
        data = _http_get(API_HOST, API_PATH)
        if data is None:
            self.error_occurred.emit("network error")
            return
        try:
            tag = data.get("tag_name", "")
            latest_ver = parse_version(tag)
            current_ver = parse_version(self._current_version)

            if latest_ver <= current_ver:
                self.up_to_date.emit()
                return

            asset_url = None
            asset_size = 0
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe") and "Windows" in name:
                    asset_url = asset.get("browser_download_url", "")
                    asset_size = asset.get("size", 0)
                    break

            if not asset_url:
                self.error_occurred.emit("no asset")
                return

            self.update_available.emit({
                "version": tag,
                "download_url": asset_url,
                "body": data.get("body", ""),
                "size": asset_size,
                "published_at": data.get("published_at", ""),
            })
        except Exception as e:
            self.error_occurred.emit(str(e))


# ── UpdateDownloader ─────────────────────────────────────────

class UpdateDownloader(QThread):
    """Background thread: downloads the new .exe to a temp file."""
    progress = Signal(int, int)
    finished = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, download_url: str, expected_size: int = 0, parent=None):
        super().__init__(parent)
        self._url = download_url
        self._expected_size = expected_size
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        dest = os.path.join(tempfile.gettempdir(), "GridFlow_update.exe")
        parsed = urlparse(self._url)
        try:
            conn = HTTPSConnection(parsed.hostname, timeout=60)
            conn.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""),
                         headers={"User-Agent": "GridFlow-Updater"})
            resp = conn.getresponse()

            # follow redirect
            if resp.status in (301, 302, 307, 308):
                redirect_url = resp.getheader("Location")
                conn.close()
                parsed = urlparse(redirect_url)
                conn = HTTPSConnection(parsed.hostname, timeout=60)
                conn.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""),
                             headers={"User-Agent": "GridFlow-Updater"})
                resp = conn.getresponse()

            size = int(resp.getheader("Content-Length", 0)) or self._expected_size
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    if self._is_cancelled:
                        f.close()
                        os.remove(dest)
                        conn.close()
                        return
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if size:
                        self.progress.emit(downloaded, size)
            conn.close()
            self.finished.emit(dest)
        except Exception as e:
            if os.path.exists(dest):
                os.remove(dest)
            self.error_occurred.emit(str(e))


# ── UpdateDialog ─────────────────────────────────────────────

class UpdateDialog(QDialog):
    """更新对话框：发现新版本 → 下载中 → 准备安装，三态都在同一个窗口完成。

    以前是「更新对话框 + 一个独立的 QProgressDialog」，进度框没有主题、没有取消，
    下载完成后直接替换并重启，用户没有感知。
    """

    RESTART_COUNTDOWN = 5          # 下载完成后自动重启的倒计时（秒）

    STATE_AVAILABLE = 0
    STATE_DOWNLOADING = 1
    STATE_READY = 2

    def __init__(self, update_info: dict, current_version: str, lang, parent=None):
        super().__init__(parent)
        self._info = update_info
        self._lang = lang
        self._current_version = current_version
        self._theme = ThemeManager.instance()
        self._downloader = None
        self._temp_path = ""
        self._countdown = 0
        self._last_bytes = 0
        self._last_time = 0.0
        self._timer = None

        self.setWindowTitle(lang.tr("update.title"))
        self.setMinimumWidth(520)
        self.setMaximumWidth(620)
        self.setModal(True)

        self._setup_ui()
        self._apply_lang()
        self._apply_style()
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._show_state(self.STATE_AVAILABLE)

    # ── 界面 ────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 20, 22, 18)

        # 头部：应用图标 + 标题 + 当前版本
        header = QHBoxLayout()
        header.setSpacing(12)
        self.icon_label = QLabel()
        pixmap = QPixmap(icon_path())
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio,
                                                    Qt.SmoothTransformation))
        self.icon_label.setFixedSize(40, 40)
        header.addWidget(self.icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_box.addWidget(self.title_label)
        self.subtitle_label = QLabel()
        title_box.addWidget(self.subtitle_label)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        self.divider = QFrame()
        self.divider.setFixedHeight(1)
        layout.addWidget(self.divider)

        # 三个状态
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_available_page())
        self.stack.addWidget(self._build_downloading_page())
        self.stack.addWidget(self._build_ready_page())
        layout.addWidget(self.stack, 1)

    def _build_available_page(self) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(10)

        info_row = QHBoxLayout()
        info_row.setSpacing(18)
        self.latest_label = QLabel()
        self.size_label = QLabel()
        self.published_label = QLabel()
        for lbl in (self.latest_label, self.size_label, self.published_label):
            info_row.addWidget(lbl)
        info_row.addStretch()
        box.addLayout(info_row)

        self.notes_title = QLabel()
        box.addWidget(self.notes_title)

        self.notes_view = QTextBrowser()
        self.notes_view.setOpenExternalLinks(True)
        self.notes_view.setMinimumHeight(220)
        box.addWidget(self.notes_view, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        box.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.ignore_btn = QPushButton()
        self.ignore_btn.clicked.connect(self._on_ignore)
        btn_row.addWidget(self.ignore_btn)
        btn_row.addStretch()
        self.later_btn = QPushButton()
        self.later_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.later_btn)
        self.download_btn = QPushButton()
        self.download_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self.download_btn)
        box.addLayout(btn_row)
        return page

    def _build_downloading_page(self) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        box.addStretch(1)

        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignCenter)
        box.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(True)
        box.addWidget(self.progress_bar)

        self.progress_detail = QLabel()
        self.progress_detail.setAlignment(Qt.AlignCenter)
        box.addWidget(self.progress_detail)

        box.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self._cancel_download)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        box.addLayout(btn_row)
        return page

    def _build_ready_page(self) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        box.addStretch(1)

        self.ready_label = QLabel()
        self.ready_label.setAlignment(Qt.AlignCenter)
        box.addWidget(self.ready_label)

        self.ready_hint = QLabel()
        self.ready_hint.setAlignment(Qt.AlignCenter)
        self.ready_hint.setWordWrap(True)
        box.addWidget(self.ready_hint)

        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        box.addWidget(self.countdown_label)

        box.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.restart_later_btn = QPushButton()
        self.restart_later_btn.clicked.connect(self._on_restart_later)
        btn_row.addWidget(self.restart_later_btn)
        self.restart_now_btn = QPushButton()
        self.restart_now_btn.clicked.connect(self._apply_update)
        btn_row.addWidget(self.restart_now_btn)
        btn_row.addStretch()
        box.addLayout(btn_row)
        return page

    # ── 文案与样式 ──────────────────────────────────────

    def _apply_lang(self):
        lang, info = self._lang, self._info
        self.title_label.setText(lang.tr("update.available_title", version=info["version"]))
        self.subtitle_label.setText(lang.tr("update.current") + f": {self._current_version}")
        self.latest_label.setText(lang.tr("update.latest") + f": {info['version']}")
        size = info.get("size") or 0
        self.size_label.setText(lang.tr("update.size") + ": "
                               + (f"{size / 1048576:.1f} MB" if size else "—"))
        published = (info.get("published_at") or "")[:10]
        self.published_label.setText(lang.tr("update.published") + ": " + (published or "—"))
        self.notes_title.setText(lang.tr("update.notes"))
        self.ignore_btn.setText(lang.tr("update.ignore"))
        self.later_btn.setText(lang.tr("update.later"))
        self.download_btn.setText(lang.tr("update.download"))
        self.progress_label.setText(lang.tr("update.downloading"))
        self.cancel_btn.setText(lang.tr("btn.cancel"))
        self.ready_label.setText(lang.tr("update.ready"))
        self.ready_hint.setText(lang.tr("update.ready_hint"))
        self.restart_now_btn.setText(lang.tr("update.restart_now"))
        self.restart_later_btn.setText(lang.tr("update.later"))

        # 更新说明：markdown 渲染（先剥 HTML 注释，避免把模板维护注释显示给用户）
        body = (info.get("body") or "").strip()
        self.notes_title.setVisible(bool(body))
        self.notes_view.setVisible(bool(body))
        self._notes_html = to_html(body) if body else ""
        if self._notes_html:
            self.notes_view.setHtml(self._notes_html)

        if self._downloader is None:
            self.status_label.setVisible(False)

    def _apply_style(self):
        c = self._theme.current_colors
        self.setStyleSheet(f"""
            QDialog {{ background-color: {c['BG_CARD']}; }}
            QLabel {{ color: {c['TEXT_PRIMARY']}; background: transparent; }}
        """)
        self.subtitle_label.setStyleSheet(f"font-size: 9.5pt; color: {c['TEXT_MUTED']};")
        self.latest_label.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {c['PRIMARY']};")
        for lbl in (self.size_label, self.published_label):
            lbl.setStyleSheet(f"font-size: 9.5pt; color: {c['TEXT_SECONDARY']};")
        self.notes_title.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {c['TEXT_SECONDARY']};")
        self.divider.setStyleSheet(f"background-color: {c['BORDER']}; border: none;")
        self.notes_view.setStyleSheet(
            f"QTextBrowser {{ background-color: {c['BG_INPUT']}; color: {c['TEXT_PRIMARY']}; "
            f"border: 1px solid {c['BORDER']}; border-radius: {c['RADIUS_SM']}px; padding: 8px 10px; }}")
        # 更新说明内部的元素样式（标题、表格边框、代码块）走文档默认样式表
        self.notes_view.document().setDefaultStyleSheet(f"""
            h1 {{ font-size: 14pt; color: {c['TEXT_PRIMARY']}; margin: 2px 0 8px 0; }}
            h2 {{ font-size: 12pt; color: {c['TEXT_PRIMARY']}; margin: 12px 0 6px 0; }}
            h3 {{ font-size: 10.5pt; color: {c['TEXT_SECONDARY']}; margin: 8px 0 4px 0; }}
            p, li, td, th {{ color: {c['TEXT_PRIMARY']}; font-size: 9.5pt; }}
            table {{ border-collapse: collapse; }}
            th {{ background-color: {c['PRIMARY_LIGHT']}; font-weight: bold; }}
            td, th {{ border: 1px solid {c['BORDER']}; padding: 3px 8px; }}
            code {{ background-color: {c['BG_MAIN']}; color: {c['PRIMARY']}; }}
            pre {{ background-color: {c['BG_MAIN']}; color: {c['TEXT_PRIMARY']}; padding: 8px; }}
            blockquote {{ color: {c['TEXT_SECONDARY']}; }}
            a {{ color: {c['PRIMARY']}; }}
        """)
        if getattr(self, "_notes_html", ""):
            self.notes_view.setHtml(self._notes_html)      # 主题切换后重排说明内容
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {c['BG_INPUT']}; border: 1px solid {c['BORDER']}; "
            f"border-radius: {c['RADIUS_SM']}px; text-align: center; color: {c['TEXT_PRIMARY']}; }} "
            f"QProgressBar::chunk {{ background-color: {c['PRIMARY']}; border-radius: 3px; }}")
        self.progress_detail.setStyleSheet(f"font-size: 9.5pt; color: {c['TEXT_SECONDARY']};")
        self.ready_hint.setStyleSheet(f"font-size: 10pt; color: {c['TEXT_SECONDARY']};")
        self.countdown_label.setStyleSheet(f"font-size: 10pt; color: {c['PRIMARY']};")
        self.restart_now_btn.setStyleSheet(
            f"QPushButton {{ background-color: {c['PRIMARY']}; color: white; border: none; "
            f"border-radius: {c['RADIUS_SM']}px; padding: 8px 20px; font-size: 11pt; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {c['PRIMARY_HOVER']}; }} "
            f"QPushButton:pressed {{ background-color: {c['PRIMARY_ACTIVE']}; }} "
            f"QPushButton:focus {{ border: 2px solid {c['PRIMARY_HOVER']}; }}")
        # 「下载更新」是主操作：实心主色；「稍后」次之；「忽略此版本」最弱
        self.download_btn.setStyleSheet(self.restart_now_btn.styleSheet())
        self.ignore_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {c['TEXT_MUTED']}; "
            f"padding: 8px 6px; font-size: 10pt; text-decoration: underline; }} "
            f"QPushButton:hover {{ color: {c['DANGER']}; }} "
            f"QPushButton:focus {{ border: 1px solid {c['PRIMARY']}; }}")
        self.status_label.setStyleSheet(f"font-size: 10pt; color: {c['DANGER']};")

    def _on_theme_changed(self, _name):
        self._apply_style()

    def _show_state(self, state: int):
        self.stack.setCurrentIndex(state)
        self.progress_label.setVisible(state == self.STATE_DOWNLOADING)

    # ── 动作 ────────────────────────────────────────────

    def _start_download(self):
        if self._downloader is not None:
            return
        self._last_bytes = 0
        self._last_time = time.time()
        self.progress_bar.setValue(0)
        self.progress_detail.setText("")
        self._show_state(self.STATE_DOWNLOADING)

        self._downloader = UpdateDownloader(
            self._info["download_url"], self._info.get("size", 0), self)
        self._downloader.progress.connect(self._on_progress)
        self._downloader.finished.connect(self._on_downloaded)
        self._downloader.error_occurred.connect(self._on_download_error)
        self._downloader.start()

    def _on_progress(self, done: int, total: int):
        if total <= 0:
            return
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(int(done * 100 / total))

        now = time.time()
        elapsed = now - self._last_time
        delta = done - self._last_bytes
        # 间隔太短（或进度没前进）时算出的速度毫无意义，只更新进度条
        if elapsed < 0.2 or delta <= 0:
            return

        speed = delta / elapsed                                   # B/s
        self._last_bytes, self._last_time = done, now
        remaining = (total - done) / speed if speed > 0 else 0
        # 单位留在文案里，这里只给数值；异常情况用 “—” 占位
        speed_text = f"{speed / 1048576:.1f}" if speed >= 8192 else "—"
        eta_text = f"{int(remaining)}" if 0 < remaining < 3600 else "—"
        self.progress_detail.setText(self._lang.tr(
            "update.download_detail",
            done=f"{done / 1048576:.1f}", total=f"{total / 1048576:.1f}",
            speed=speed_text, eta=eta_text,
        ))

    def _on_downloaded(self, path: str):
        self._temp_path = path
        self._stop_downloader()
        self._show_state(self.STATE_READY)
        self._countdown = self.RESTART_COUNTDOWN
        self.countdown_label.setText(
            self._lang.tr("update.countdown", n=self._countdown))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_countdown)
        self._timer.start(1000)

    def _tick_countdown(self):
        self._countdown -= 1
        if self._countdown <= 0:
            self._timer.stop()
            self._apply_update()
            return
        self.countdown_label.setText(self._lang.tr("update.countdown", n=self._countdown))

    def _apply_update(self):
        if getattr(self, "_timer", None) is not None:
            self._timer.stop()
        if not self._temp_path:
            self.reject()
            return
        apply_update_and_restart(self._temp_path)

    def _on_restart_later(self):
        """稍后：本次不安装（安装包留在临时目录，下次检查更新会重新下载）。"""
        if getattr(self, "_timer", None) is not None:
            self._timer.stop()
        self.reject()

    def _cancel_download(self):
        if self._downloader is not None:
            self._downloader.cancel()
            self._stop_downloader()
        self._show_state(self.STATE_AVAILABLE)
        self.status_label.setText(self._lang.tr("update.download_cancelled"))
        self.status_label.setVisible(True)

    def _on_download_error(self, message: str):
        self._stop_downloader()
        self._show_state(self.STATE_AVAILABLE)
        self.download_btn.setText(self._lang.tr("update.retry"))
        self.status_label.setText(f"{self._lang.tr('update.download_error')}: {message}")
        self.status_label.setVisible(True)

    def _stop_downloader(self):
        """回收下载线程，避免关闭对话框时留下运行中的 QThread。"""
        downloader = self._downloader
        self._downloader = None
        if downloader is None:
            return
        if downloader.isRunning():
            downloader.cancel()
            downloader.wait(3000)
        downloader.deleteLater()

    def _on_ignore(self):
        from app.settings import set_ignored_version
        set_ignored_version(self._info["version"])
        self.reject()

    def reject(self):
        self._stop_downloader()
        if getattr(self, "_timer", None) is not None:
            self._timer.stop()
        super().reject()

    def closeEvent(self, event):
        self._stop_downloader()
        if getattr(self, "_timer", None) is not None:
            self._timer.stop()
        super().closeEvent(event)


# ── cache helpers ────────────────────────────────────────────

def get_last_check_time() -> float:
    from app.settings import _settings
    return float(_settings.value("update/last_check", 0) or 0)


def set_last_check_time():
    from app.settings import _settings
    _settings.setValue("update/last_check", int(time.time()))


def should_auto_check() -> bool:
    return (time.time() - get_last_check_time()) > CHECK_INTERVAL


# ── .bat installer ───────────────────────────────────────────

def apply_update_and_restart(tmp_exe: str):
    """Write .bat script, launch it, exit current process."""
    old = sys.executable
    bat = os.path.join(tempfile.gettempdir(), "gridflow_updater.bat")
    script = f'''@echo off
chcp 65001 >nul
echo Updating GridFlow...
:wait
timeout /t 2 /nobreak >nul
move /Y "{tmp_exe}" "{old}"
if %errorlevel% neq 0 (
    echo Update failed. Please reinstall manually.
    pause
    exit /b 1
)
start "" "{old}"
del "%~f0"
'''
    with open(bat, "w", encoding="utf-8") as f:
        f.write(script)

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(
        ["cmd.exe", "/c", bat],
        startupinfo=si,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)
