from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="sqlite:///./test.db")
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BaiduYun Tools"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # 上传目录
    UPLOAD_DIR: str = Field(default="./uploads")
    
    class Config:
        env_file = ".env"

settings = Settings()

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
