import logging
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import (
    MeetingMinutesException,
    get_user_friendly_error
)
from app.models.database import init_db, close_db
from app.api.upload import router as upload_router
from app.api.meetings import router as meetings_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    await init_db()
    yield
    # 关闭时执行
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 全局异常处理器 ==========

@app.exception_handler(MeetingMinutesException)
async def meeting_minutes_exception_handler(request: Request, exc: MeetingMinutesException):
    """处理自定义异常"""
    logger.error(f"MeetingMinutesException: {exc.message}", exc_info=True)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 9999,
            "message": get_user_friendly_error(exc),
            "data": None
        }
    )


# 注册路由
app.include_router(upload_router)
app.include_router(meetings_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# ========== 前端静态文件服务 ==========

_dist_dir = Path(settings.FRONTEND_DIST_DIR).resolve()

if _dist_dir.exists():
    # 挂载 assets 子目录，享受 StaticFiles 的高效文件服务
    _assets_dir = _dist_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")
    logger.info(f"Frontend dist found at {_dist_dir}, serving SPA.")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """为 Vue SPA 提供静态文件服务，未匹配的路径回退到 index.html"""
        file_path = _dist_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_dist_dir / "index.html"))

else:
    logger.warning(
        f"Frontend dist not found at {_dist_dir}. "
        "Run `npm run build` in the frontend directory first."
    )

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "status": "running",
            "note": "Frontend not built. Run `npm run build` in frontend/."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG
    )
