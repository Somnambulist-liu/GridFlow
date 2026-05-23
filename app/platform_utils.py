"""Cross-platform utilities for file operations."""
import os
import subprocess
import sys


def open_file_explorer(path: str):
    """Open the file explorer/finder at the given path."""
    path = os.path.abspath(path)
    if sys.platform == "win32":
        subprocess.run(["explorer", path])
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


def open_file(path: str):
    """Open a file with the default application."""
    path = os.path.abspath(path)
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])
