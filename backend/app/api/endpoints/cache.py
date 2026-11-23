from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

from ...core.cache_locator import find_cache_files, validate_cache_file
from ...db.sqlite_utils import SQLiteManager
from .database import set_current_db, get_current_db

router = APIRouter()


@router.get("/find-cache")
def find_cache() -> Dict:
    """扫描本机百度网盘客户端的缓存数据库"""
    try:
        return find_cache_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查找缓存失败: {e}")


class LoadDbRequest(BaseModel):
    path: str


@router.post("/load-db")
def load_db(req: LoadDbRequest) -> Dict:
    """直接加载指定路径的缓存数据库（不复制文件）"""
    try:
        info = validate_cache_file(req.path)
        db = SQLiteManager(req.path)
        stats = db.get_database_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载数据库失败: {e}")

    set_current_db(req.path)
    return {
        "db_path": req.path,
        "name": info["name"],
        "kind": info["kind"],
        "record_count": info["record_count"],
        "directory_count": stats["dir_count"],
        "file_count": stats["file_count"],
        "total_size": stats["total_size"],
    }


@router.get("/current-db")
def current_db() -> Dict:
    return {"db_path": get_current_db()}
