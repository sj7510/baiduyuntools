"""桌面端入口：启动内置 HTTP 服务，并用原生窗口或 Edge 应用窗口展示界面。"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

APP_TITLE = "百度云工具"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _setup_logging() -> Path:
    from app.core.paths import log_dir

    log_file = log_dir() / "app.log"
    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    return log_file


def _wait_ready(url: str, timeout: float = 20.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def _find_edge() -> str | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _open_window(url: str) -> None:
    """优先使用 pywebview 原生窗口，其次 Edge 应用模式，最后默认浏览器。"""
    try:
        import webview  # type: ignore

        window = webview.create_window(APP_TITLE, url, width=1440, height=900, min_size=(1024, 640))
        webview.start()
        return
    except Exception as e:  # noqa: BLE001 - 保底方案需要吞掉所有异常
        logging.warning("原生窗口启动失败，回退到浏览器：%s", e)

    edge = _find_edge()
    if edge:
        proc = subprocess.Popen(
            [edge, f"--app={url}", "--window-size=1440,900", "--disable-features=msEdgeSidebarV2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()
        return

    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main() -> None:
    # 允许在后台以无界面模式启动，便于自动化验证
    headless = os.environ.get("BAIDUYUN_HEADLESS") == "1"
    log_file = _setup_logging()
    logging.info("启动 %s，日志：%s", APP_TITLE, log_file)

    port = int(os.environ.get("BAIDUYUN_PORT") or 0) or _free_port()
    os.environ.setdefault("BAIDUYUN_PORT", str(port))

    import uvicorn
    from app.main import app

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    if not _wait_ready(url):
        logging.error("服务启动超时")
        raise SystemExit(1)

    logging.info("服务已就绪：%s", url)
    try:
        print(f"{APP_TITLE} 已启动：{url}")
    except Exception:
        pass

    if headless:
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
        return

    try:
        _open_window(url)
    finally:
        server.should_exit = True
        thread.join(timeout=10)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - 打包后需要把错误展示给用户
        logging.exception("启动失败")
        message = f"启动失败：{exc}\n\n日志文件：%LOCALAPPDATA%\\BaiduYunTools\\logs\\app.log"
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, APP_TITLE, 0x10)
            except Exception:
                pass
        raise
