# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：单文件桌面版百度云工具。"""

import os
from PyInstaller.utils.hooks import collect_submodules

project_root = os.path.abspath(SPECPATH)
backend_dir = os.path.join(project_root, "backend")
static_dir = os.path.join(backend_dir, "static")

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "app.api.endpoints.cache",
    "app.api.endpoints.database",
    "app.core.cache_locator",
    "app.core.paths",
]

webview_modules = collect_submodules("webview")
excluded_webview = {
    "webview.platforms.gtk",
    "webview.platforms.qt",
    "webview.platforms.cef",
    "webview.platforms.cocoa",
    "webview.platforms.wkwebview",
    "webview.platforms.android",
    "webview.platforms.xdgdesktopportal",
}
hiddenimports += [m for m in webview_modules if m not in excluded_webview]

a = Analysis(
    [os.path.join(backend_dir, "desktop.py")],
    pathex=[backend_dir],
    binaries=[],
    datas=[(static_dir, "static")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "plotly",
        "kaleido",
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
        "sqlalchemy",
        "aiosqlite",
        "pytest",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BaiduYunTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
