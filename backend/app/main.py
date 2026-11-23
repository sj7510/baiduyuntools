from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core import paths
from app.api.endpoints.database import router as database_router
from app.api.endpoints.cache import router as cache_router
import os
import shutil
from pathlib import Path
from typing import Optional
from app.api.endpoints.database import get_directory_tree, get_database_info
from app.api.endpoints.database import clear_current_db

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

# 上传目录配置（打包后位于 %LOCALAPPDATA%\BaiduYunTools\uploads）
UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 静态文件目录配置（打包后从 PyInstaller 解包目录读取）
STATIC_DIR = str(paths.static_dir())

# 注册API路由
app.include_router(database_router, prefix=settings.API_V1_STR, tags=["database"])
app.include_router(cache_router, prefix=settings.API_V1_STR, tags=["cache"])

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
        # 只允许删除上传目录中的副本，避免误删客户端原始缓存
        upload_root = os.path.abspath(UPLOAD_DIR)
        candidate = os.path.abspath(db_path)
        if os.path.commonpath([upload_root, candidate]) != upload_root:
            candidate = os.path.join(upload_root, os.path.basename(db_path))

        if not os.path.exists(candidate):
            # 直接加载的原始缓存不在上传目录中，无需删除，仅清除当前状态
            clear_current_db()
            return {"message": "Database cleared"}

        os.remove(candidate)
        clear_current_db()
        return {"message": "Database deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
