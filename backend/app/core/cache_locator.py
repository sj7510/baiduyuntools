"""自动定位百度网盘客户端的文件缓存数据库。

支持两类缓存：
- 旧版客户端：BaiduYunCacheFileV0.db（表 cache_file）
- 新版客户端：filecache.db（表 file_meta）
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

DB_FILENAMES = {"baiduyuncachefilev0.db", "filecache.db"}
MAX_DEPTH = 6
VALID_TABLES = {"cache_file", "file_meta"}


def _baidu_collation(a: str, b: str) -> int:
    """百度网盘数据库使用了自定义排序规则 baidunetdisksort，这里提供等价兜底。"""
    a = a or ""
    b = b or ""
    return (a > b) - (a < b)


def _is_windows() -> bool:
    return os.name == "nt"


def _registry_install_dirs() -> List[str]:
    """从注册表卸载项中取出百度网盘安装目录"""
    if not _is_windows():
        return []
    try:
        import winreg
    except ImportError:
        return []

    roots = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    dirs: List[str] = []
    for hive, subkey in roots:
        try:
            key = winreg.OpenKey(hive, subkey)
        except OSError:
            continue
        with key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, name) as item:
                        display = str(winreg.QueryValueEx(item, "DisplayName")[0])
                        if not any(k in display for k in ("百度网盘", "BaiduNetdisk", "BaiduYunGuanjia")):
                            continue
                        location = str(winreg.QueryValueEx(item, "InstallLocation")[0])
                        if location and os.path.isdir(location):
                            dirs.append(location)
                except OSError:
                    continue
    return dirs


def _candidate_roots() -> List[str]:
    roots: List[str] = []

    appdata = os.environ.get("APPDATA")
    localappdata = os.environ.get("LOCALAPPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    for base in (appdata, localappdata):
        if base:
            roots.append(os.path.join(base, "baidu"))
            roots.append(os.path.join(base, "Baidu"))

    installs = _registry_install_dirs()
    installs += [
        r"C:\Program Files (x86)\Baidu\BaiduYunGuanjia",
        r"C:\Program Files\Baidu\BaiduYunGuanjia",
        r"C:\Program Files (x86)\Baidu\BaiduNetdisk",
        r"C:\Program Files\Baidu\BaiduNetdisk",
    ]
    installs += [os.path.join(programdata, "baidu")] if programdata else []

    for drive in "CDEFG":
        for name in ("BaiduNetdisk", "BaiduYunGuanjia"):
            installs.append(f"{drive}:\\{name}")

    for install in installs:
        if not os.path.isdir(install):
            continue
        root = os.path.normpath(install)
        if root not in roots:
            roots.append(root)
        # 新版客户端的账户缓存目录
        for sub in (("module", "BrowserEngine", "users"), ("users",)):
            path = os.path.join(root, *sub)
            if os.path.isdir(path) and path not in roots:
                roots.append(path)

    return roots


def _walk_files(roots: Iterable[str], max_depth: int = MAX_DEPTH) -> Iterable[str]:
    """在候选根目录中递归查找缓存文件名"""
    seen_dirs = set()
    for root in roots:
        root = os.path.normpath(root)
        if not os.path.isdir(root) or root in seen_dirs:
            continue
        seen_dirs.add(root)
        base_depth = root.rstrip("\\/").count(os.sep)
        for current, dirs, files in os.walk(root, followlinks=False):
            depth = current.rstrip("\\/").count(os.sep) - base_depth
            if depth >= max_depth:
                dirs[:] = []
            # 跳过明显的非账户目录，减少全盘遍历成本
            dirs[:] = [d for d in dirs if d.lower() not in ("cache", "temp", "logs", "log")]
            for filename in files:
                if filename.lower() in DB_FILENAMES:
                    yield os.path.join(current, filename)


def _inspect(path: str) -> Optional[Dict]:
    """校验 sqlite 结构并返回缓存信息"""
    try:
        size = os.path.getsize(path)
        if size <= 0:
            return None
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        try:
            conn.create_collation("baidunetdisksort", _baidu_collation)
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if not (tables & VALID_TABLES):
                return None
            table = "cache_file" if "cache_file" in tables else "file_meta"
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            conn.close()
        mtime = os.path.getmtime(path)
        return {
            "path": path,
            "name": os.path.basename(path),
            "size": size,
            "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
            "modified_ts": mtime,
            "kind": "legacy" if table == "cache_file" else "new",
            "record_count": count,
        }
    except (sqlite3.Error, OSError) as e:
        logger.debug("检查缓存文件失败 %s: %s", path, e)
        return None


def find_cache_files() -> Dict:
    """查找本机所有可用的百度网盘缓存数据库"""
    started = time.time()
    roots = _candidate_roots()
    found: List[Dict] = []
    checked = 0
    for path in _walk_files(roots):
        checked += 1
        info = _inspect(path)
        if info:
            found.append(info)

    # 同一路径去重，按修改时间倒序
    unique: Dict[str, Dict] = {}
    for item in found:
        unique[os.path.normcase(item["path"])] = item
    result = sorted(unique.values(), key=lambda x: x["modified_ts"], reverse=True)
    for item in result:
        item.pop("modified_ts", None)

    logger.info("缓存查找完成：扫描 %d 个候选文件，命中 %d 个，耗时 %.1fs",
                checked, len(result), time.time() - started)
    return {
        "found": result,
        "roots": roots,
        "scanned_files": checked,
        "elapsed": round(time.time() - started, 1),
    }


def validate_cache_file(path: str) -> Dict:
    """校验指定路径是否为可用的缓存数据库"""
    if not path:
        raise ValueError("路径不能为空")
    if not os.path.isfile(path):
        raise ValueError("文件不存在")
    info = _inspect(path)
    if not info:
        raise ValueError("不是有效的百度网盘缓存数据库（缺少 cache_file / file_meta 表）")
    return info
