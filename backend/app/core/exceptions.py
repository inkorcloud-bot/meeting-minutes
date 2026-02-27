"""
异常处理和重试机制模块

提供统一的异常处理、错误响应和重试装饰器
"""

import logging
import functools
import asyncio
from typing import Type, Tuple, Callable, Any, Optional
from fastapi import HTTPException, status
from httpx import HTTPError, TimeoutException, ConnectError

logger = logging.getLogger(__name__)


# ========== 自定义异常类 ==========

class MeetingMinutesException(Exception):
    """会议纪要系统基础异常类"""
    
    def __init__(self, message: str, code: int = 1, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class FileValidationError(MeetingMinutesException):
    """文件验证错误"""
    
    def __init__(self, message: str):
        super().__init__(message, code=1001, status_code=400)


class ASRServiceError(MeetingMinutesException):
    """ASR 服务错误"""
    
    def __init__(self, message: str):
        super().__init__(message, code=2001, status_code=502)


class LLMServiceError(MeetingMinutesException):
    """大模型服务错误"""
    
    def __init__(self, message: str):
        super().__init__(message, code=2002, status_code=502)


class DatabaseError(MeetingMinutesException):
    """数据库错误"""
    
    def __init__(self, message: str):
        super().__init__(message, code=3001, status_code=500)


class NotFoundError(MeetingMinutesException):
    """资源未找到错误"""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code=4001, status_code=404)


# ========== 重试装饰器 ==========

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (
        HTTPError,
        TimeoutException,
        ConnectError,
        ConnectionError,
        asyncio.TimeoutError
    ),
    logger_instance: Optional[logging.Logger] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    异步函数重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数（指数退避）
        exceptions: 需要重试的异常类型
        logger_instance: 日志记录器实例
        on_retry: 重试时的回调函数，接收 (attempt, exception)
    
    Returns:
        装饰器函数
    """
    log = logger_instance or logger
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        log.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}. Retrying in {current_delay:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        log.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}"
                        )
            
            # 所有重试都失败，抛出最后一个异常
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# ========== 异常处理工具函数 ==========

def exception_to_http_exception(exc: Exception) -> HTTPException:
    """
    将自定义异常转换为 HTTPException
    
    Args:
        exc: 异常实例
    
    Returns:
        HTTPException 实例
    """
    if isinstance(exc, MeetingMinutesException):
        return HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.message
            }
        )
    elif isinstance(exc, HTTPException):
        return exc
    else:
        # 未知异常，包装为 500 错误
        logger.error(f"Unexpected error: {type(exc).__name__}: {exc}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 9999,
                "message": f"服务器内部错误: {str(exc)}"
            }
        )


def get_user_friendly_error(exc: Exception) -> str:
    """
    获取用户友好的错误信息
    
    Args:
        exc: 异常实例
    
    Returns:
        用户友好的错误信息
    """
    if isinstance(exc, FileValidationError):
        return f"文件验证失败：{exc.message}"
    elif isinstance(exc, ASRServiceError):
        return f"语音识别服务暂时不可用，请稍后重试。错误：{exc.message}"
    elif isinstance(exc, LLMServiceError):
        return f"智能摘要服务暂时不可用，请稍后重试。错误：{exc.message}"
    elif isinstance(exc, DatabaseError):
        return "数据访问出错，请稍后重试"
    elif isinstance(exc, NotFoundError):
        return exc.message
    elif isinstance(exc, HTTPException):
        if isinstance(exc.detail, dict):
            return exc.detail.get("message", str(exc.detail))
        return str(exc.detail)
    else:
        return "操作失败，请稍后重试"
