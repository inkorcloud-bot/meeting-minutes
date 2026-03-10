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
    LLM_TEMPERATURE: float = 0.4
    LLM_TOP_P: float = 0.85
    LLM_THINKING_BUDGET: int = 10000  # 深度思考 token 预算（DeepSeek 等）
    LLM_MAX_TOKENS: int = 6000  # 单次响应最大输出 token 数
    
    # 前端静态文件目录（相对于 backend/ 运行目录）
    FRONTEND_DIST_DIR: str = "../frontend/dist"

    # 文件存储配置
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 524288000  # 500MB in bytes
    
    # ASR 轮询配置（大音频文件推理耗时较长，适当增加等待时间）
    ASR_POLL_INTERVAL: float = 5.0  # 轮询间隔（秒）
    ASR_MAX_POLLS: int = 720  # 最大轮询次数（默认 720 次 = 60 分钟）

    # LLM 并发控制：同时最多允许 N 个任务调用 LLM，其余在队列中等待
    LLM_CONCURRENCY: int = 2
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
