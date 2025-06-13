from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.endpoints.database import router as database_router
import os
import shutil
from pathlib import Path
from typing import Optional
from app.api.endpoints.database import get_directory_tree, get_database_info

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传目录配置
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 静态文件目录配置
STATIC_DIR = "static"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# 注册API路由
app.include_router(database_router, prefix=settings.API_V1_STR, tags=["database"])

# 处理根路径请求
@app.get("/")
async def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# 处理所有其他静态文件请求
@app.get("/{path:path}")
async def serve_static(path: str):
    static_path = os.path.join(STATIC_DIR, path)
    if os.path.exists(static_path) and os.path.isfile(static_path):
        return FileResponse(static_path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.delete("/api/v1/delete-db/{db_path:path}")
async def delete_database(db_path: str):
    try:
        # 检查文件是否存在
        if not os.path.exists(db_path):
            # 尝试在上传目录中查找
            full_path = os.path.join(UPLOAD_DIR, os.path.basename(db_path))
            if not os.path.exists(full_path):
                raise HTTPException(status_code=404, detail="Database file not found")
            db_path = full_path
            
        # 删除文件
        os.remove(db_path)
        return {"message": "Database deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/database-info")
async def get_db_info(db_path: Optional[str] = None):
    try:
        if db_path:
            # 如果提供了数据库路径，直接使用
            if not os.path.exists(db_path):
                # 尝试在上传目录中查找
                full_path = os.path.join(UPLOAD_DIR, os.path.basename(db_path))
                if not os.path.exists(full_path):
                    raise HTTPException(status_code=404, detail="Database file not found")
                db_path = full_path
        else:
            # 否则获取上传目录中最新的数据库文件
            db_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.db')]
            if not db_files:
                raise HTTPException(status_code=404, detail="No database file found")
                
            # 使用最新的数据库文件
            latest_db = max(db_files, key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)))
            db_path = os.path.join(UPLOAD_DIR, latest_db)
        
        # 获取数据库统计信息
        stats = await get_database_info(db_path=db_path)
        return {
            "name": os.path.basename(db_path),
            "dir_count": stats["dir_count"],
            "file_count": stats["file_count"],
            "total_size": stats["total_size"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
