from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Dict, List
import os
import shutil
import logging
from ...db.sqlite_utils import SQLiteManager
from ...core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 存储当前加载的数据库路径
current_db: str = None

@router.post("/upload-db")
async def upload_database(file: UploadFile = File(...)) -> Dict:
    """上传数据库文件"""
    global current_db
    
    logger.info(f"接收到数据库文件上传请求: {file.filename}")
    
    if not file.filename.endswith('.db'):
        logger.warning(f"文件类型不正确: {file.filename}")
        raise HTTPException(status_code=400, detail="只接受.db文件")
    
    # 确保上传目录存在
    upload_dir = os.path.join(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    logger.info(f"上传目录: {upload_dir}")
    
    # 保存文件
    file_path = os.path.join(upload_dir, file.filename)
    logger.info(f"保存文件到: {file_path}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info("文件保存成功")
    except Exception as e:
        logger.error(f"保存文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
    
    current_db = file_path
    logger.info(f"当前数据库设置为: {current_db}")
    return {"db_path": file_path}

@router.get("/database-info")
async def get_database_info(db_path: str = Query(..., description="数据库文件路径")) -> Dict:
    """获取数据库信息"""
    logger.info(f"获取数据库信息: {db_path}")
    try:
        db = SQLiteManager(db_path)
        info = db.get_database_info()
        logger.info(f"数据库信息: {info}")
        return info
    except Exception as e:
        logger.error(f"获取数据库信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/directory-tree/{path:path}")
async def get_directory_tree(path: str) -> Dict:
    """获取目录树及大小信息"""
    logger.info(f"获取目录树: {path}")
    logger.info(f"当前数据库: {current_db}")
    
    if not current_db:
        logger.error("未加载数据库")
        raise HTTPException(status_code=400, detail="未加载数据库")
        
    try:
        db = SQLiteManager(current_db)
        result = db.get_directory_tree(path)
        logger.info(f"目录树节点数量: {len(result.get('children', []))}")
        return result
    except Exception as e:
        logger.error(f"获取目录树失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/directory-size/{path:path}")
async def get_directory_size(path: str) -> Dict:
    """获取目录大小分布"""
    logger.info(f"获取目录大小: {path}")
    
    if not current_db:
        logger.error("未加载数据库")
        raise HTTPException(status_code=400, detail="未加载数据库")
        
    try:
        db = SQLiteManager(current_db)
        size_info = db.get_directory_size(path)
        logger.info(f"目录项目数量: {len(size_info['items'])}")
        return size_info
    except Exception as e:
        logger.error(f"获取目录大小失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/large-files/{path:path}")
async def get_large_files(path: str, min_size: int = 100 * 1024 * 1024) -> List[Dict]:
    """获取指定节点下大文件列表，默认100M以上，按文件大小倒序"""
    logger.info(f"获取大文件: {path}, min_size={min_size}")
    if not current_db:
        logger.error("未加载数据库")
        raise HTTPException(status_code=400, detail="未加载数据库")
    try:
        db = SQLiteManager(current_db)
        files = db.get_large_files(path, min_size)
        logger.info(f"大文件数量: {len(files)}")
        return files
    except Exception as e:
        logger.error(f"获取大文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/duplicate-files/{path:path}")
async def get_duplicate_files(path: str, min_size: int = 10 * 1024 * 1024) -> List[Dict]:
    """获取指定节点下重复文件列表，默认10M以上，按文件大小倒序"""
    logger.info(f"获取重复文件: {path}, min_size={min_size}")
    if not current_db:
        logger.error("未加载数据库")
        raise HTTPException(status_code=400, detail="未加载数据库")
    try:
        db = SQLiteManager(current_db)
        files = db.get_duplicate_files(path, min_size)
        logger.info(f"重复文件组数量: {len(files)}")
        return files
    except Exception as e:
        logger.error(f"获取重复文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 