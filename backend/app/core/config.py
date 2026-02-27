from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置管理"""
    
    # 应用基本配置
    APP_NAME: str = "Meeting Minutes System"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./meetings.db"
    
    # ASR 服务配置
    ASR_API_URL: str = "http://localhost:8000/api/v1"
    
    # 大模型配置
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    
    # 文件存储配置
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 524288000  # 500MB in bytes
    
    # ASR 轮询配置
    ASR_POLL_INTERVAL: float = 3.0  # 轮询间隔（秒）
    ASR_MAX_POLLS: int = 120  # 最大轮询次数（默认 120 次 = 10 分钟）
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
