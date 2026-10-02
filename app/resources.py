"""资源路径解析：开发环境与 PyInstaller 打包后统一入口。

注意 QSS 里的 ``url()`` 是相对**工作目录**解析的，直接写 ``resources/xxx.png``
在用户从别处启动时会加载失败；这里统一返回绝对路径（正斜杠，Qt 友好）。
"""
import os
import sys


def resource_dir() -> str:
    """返回 resources 目录的绝对路径（打包后指向 _MEIPASS/resources）。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, "resources")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "resources")


def resource_path(name: str) -> str:
    """返回资源绝对路径（不存在时也返回路径，交由调用方判断）。"""
    return os.path.join(resource_dir(), name).replace("\\", "/")


def qss_url(name: str) -> str:
    """QSS 用的 url(...) 片段，例如 image: {qss_url('check.png')};"""
    return f'url("{resource_path(name)}")'


def icon_path() -> str:
    """应用图标：Windows 用 .ico，其它平台用 .png（与打包 datas 保持一致）。"""
    name = "icon.ico" if sys.platform == "win32" else "icon.png"
    return resource_path(name)
