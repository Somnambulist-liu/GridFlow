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

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit,
)


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
    """Modal dialog showing update info with [Ignore] [Later] [Download]."""

    def __init__(self, update_info: dict, current_version: str, lang, parent=None):
        super().__init__(parent)
        self._info = update_info
        self._lang = lang
        self._current_version = current_version
        self.setWindowTitle(lang.tr("update.title"))
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # version info
        ver_layout = QHBoxLayout()
        cur = QLabel(f"{self._lang.tr('update.current')}: {self._current_version}")
        cur.setStyleSheet("font-size: 10pt; color: #64748B;")
        ver_layout.addWidget(cur)
        ver_layout.addStretch()
        latest = QLabel(f"{self._lang.tr('update.latest')}: {self._info['version']}")
        latest.setStyleSheet("font-size: 11pt; font-weight: bold; color: #2563EB;")
        ver_layout.addWidget(latest)
        layout.addLayout(ver_layout)

        # release notes
        body = self._info.get("body", "")
        if body:
            notes_label = QLabel("Release Notes:")
            notes_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
            layout.addWidget(notes_label)
            notes_text = QTextEdit()
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(200)
            notes_text.setPlainText(body[:2000])
            layout.addWidget(notes_text)

        # buttton row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        ignore_btn = QPushButton(self._lang.tr("update.ignore"))
        ignore_btn.clicked.connect(self._on_ignore)
        btn_row.addWidget(ignore_btn)

        later_btn = QPushButton(self._lang.tr("update.later"))
        later_btn.clicked.connect(self.reject)
        btn_row.addWidget(later_btn)

        self._download_btn = QPushButton(self._lang.tr("update.download"))
        self._download_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._download_btn)

        layout.addLayout(btn_row)

    def _on_ignore(self):
        from app.settings import set_ignored_version
        set_ignored_version(self._info["version"])
        self.reject()


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
