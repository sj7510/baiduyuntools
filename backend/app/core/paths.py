"""运行路径适配：开发环境与 PyInstaller 打包后的资源/数据目录。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "BaiduYunTools"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """只读资源目录（打包后为 PyInstaller 解包目录）。"""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def static_dir() -> Path:
    return resource_dir() / "static"


def user_data_dir() -> Path:
    """可写数据目录：打包后放到 %LOCALAPPDATA%，避免写入程序目录。"""
    if not is_frozen():
        return resource_dir()
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def upload_dir() -> Path:
    path = user_data_dir() / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
