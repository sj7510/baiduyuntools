from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict
import sqlite3
import os
from app.db.database import get_db

router = APIRouter()

@router.post("/upload-db")
async def upload_database(file: UploadFile = File(...)):
    """上传数据库文件"""
    try:
        # 保存上传的文件
        file_location = f"temp_{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
        return {"filename": file.filename, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/directory-tree/{path:path}")
async def get_directory_tree(path: str, db: Session = Depends(get_db)):
    """获取目录树结构"""
    try:
        query = """
        SELECT id, server_filename, file_size, isdir
        FROM cache_file
        WHERE parent_path = ?
        ORDER BY isdir DESC, server_filename
        """
        result = db.execute(query, [path]).fetchall()
        return [{"id": r[0], "name": r[1], "size": r[2], "isdir": r[3]} for r in result]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/directory-size/{path:path}")
async def get_directory_size(path: str, db: Session = Depends(get_db)):
    """获取目录大小统计"""
    try:
        query = """
        SELECT server_filename, file_size, isdir
        FROM cache_file
        WHERE parent_path = ?
        """
        result = db.execute(query, [path]).fetchall()
        
        # 处理数据
        items = []
        for name, size, isdir in result:
            if isdir:
                # 计算文件夹大小
                subquery = """
                SELECT SUM(file_size)
                FROM cache_file
                WHERE parent_path LIKE ? || '%'
                AND isdir = 0
                """
                folder_path = f"{path}{name}/" if path.endswith('/') else f"{path}/{name}/"
                total_size = db.execute(subquery, [folder_path]).scalar() or 0
                items.append({"name": name, "value": total_size, "isdir": True})
            else:
                items.append({"name": name, "value": size, "isdir": False})
        
        return {
            "items": sorted(items, key=lambda x: x["value"], reverse=True),
            "total": sum(item["value"] for item in items)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
