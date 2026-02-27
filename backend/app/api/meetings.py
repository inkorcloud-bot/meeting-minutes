"""会议管理 API 接口"""
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    DatabaseError,
    MeetingMinutesException,
    exception_to_http_exception,
    get_user_friendly_error
)
from app.models.database import Meeting, async_session
from app.models.schemas import (
    MeetingListResponse,
    MeetingListResponseData,
    MeetingListItem,
    MeetingResponse,
    MeetingResponseData,
    StatusResponse,
    StatusResponseData,
    DataResponse,
    BaseResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


async def get_db():
    """获取数据库会话依赖"""
    async with async_session() as session:
        yield session


async def get_meeting_or_404(
    meeting_id: str,
    db: AsyncSession
) -> Meeting:
    """
    获取会议记录，如果不存在则抛出 404 错误
    
    Args:
        meeting_id: 会议ID
        db: 数据库会话
        
    Returns:
        Meeting 实例
        
    Raises:
        NotFoundError: 当会议不存在时
    """
    try:
        result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError(f"会议不存在: {meeting_id}")
        
        return meeting
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Database error while fetching meeting {meeting_id}: {str(e)}", exc_info=True)
        raise DatabaseError(f"获取会议信息失败: {str(e)}")


@router.get("", response_model=MeetingListResponse)
async def get_meetings(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议列表
    
    - **skip**: 跳过数量
    - **limit**: 返回数量限制
    - **status**: 可选，按状态过滤
    """
    try:
        # 验证分页参数
        if skip < 0:
            raise HTTPException(status_code=400, detail="skip 参数不能为负数")
        
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit 参数必须在 1-1000 之间")
        
        # 验证状态参数
        valid_statuses = {'uploaded', 'processing', 'transcribing', 'summarizing', 'completed', 'failed'}
        if status and status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的状态值。支持的状态: {', '.join(valid_statuses)}"
            )
        
        # 构建查询
        query = select(Meeting)
        
        if status:
            query = query.where(Meeting.status == status)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # 获取列表
        query = query.order_by(Meeting.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        meetings = result.scalars().all()
        
        # 转换为响应模型
        items = [
            MeetingListItem(
                id=meeting.id,
                title=meeting.title,
                status=meeting.status,
                progress=meeting.progress,
                created_at=meeting.created_at
            )
            for meeting in meetings
        ]
        
        return MeetingListResponse(
            code=0,
            message="success",
            data=MeetingListResponseData(total=total, items=items)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching meeting list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 9999,
                "message": get_user_friendly_error(e)
            }
        )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议详情
    
    - **meeting_id**: 会议ID
    """
    try:
        meeting = await get_meeting_or_404(meeting_id, db)
        
        return MeetingResponse(
            code=0,
            message="success",
            data=MeetingResponseData(
                id=meeting.id,
                title=meeting.title,
                status=meeting.status,
                audio_path=meeting.audio_path,
                audio_duration=meeting.audio_duration,
                transcript=meeting.transcript,
                summary=meeting.summary,
                progress=meeting.progress,
                current_step=meeting.current_step,
                error=meeting.error,
                created_at=meeting.created_at,
                updated_at=meeting.updated_at
            )
        )
        
    except MeetingMinutesException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Error fetching meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 9999,
                "message": get_user_friendly_error(e)
            }
        )


@router.get("/{meeting_id}/status", response_model=StatusResponse)
async def get_meeting_status(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议状态和进度
    
    - **meeting_id**: 会议ID
    """
    try:
        meeting = await get_meeting_or_404(meeting_id, db)
        
        return StatusResponse(
            code=0,
            message="success",
            data=StatusResponseData(
                meeting_id=meeting.id,
                status=meeting.status,
                progress=meeting.progress,
                current_step=meeting.current_step,
                error=meeting.error
            )
        )
        
    except MeetingMinutesException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Error fetching meeting status {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 9999,
                "message": get_user_friendly_error(e)
            }
        )


@router.get("/{meeting_id}/summary", response_model=DataResponse)
async def get_meeting_summary(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议纪要
    
    - **meeting_id**: 会议ID
    """
    try:
        meeting = await get_meeting_or_404(meeting_id, db)
        
        if not meeting.summary:
            if meeting.status == 'failed':
                error_msg = meeting.error or "处理失败，无法生成会议纪要"
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 4002,
                        "message": f"会议处理失败: {error_msg}"
                    }
                )
            elif meeting.status != 'completed':
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 4001,
                        "message": f"会议纪要尚未生成，当前状态: {meeting.status}"
                    }
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": 4003,
                        "message": "会议纪要不可用"
                    }
                )
        
        return DataResponse(
            code=0,
            message="success",
            data={"meeting_id": meeting.id, "summary": meeting.summary}
        )
        
    except MeetingMinutesException as e:
        raise exception_to_http_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching meeting summary {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 9999,
                "message": get_user_friendly_error(e)
            }
        )


@router.delete("/{meeting_id}", response_model=BaseResponse)
async def delete_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除会议
    
    - **meeting_id**: 会议ID
    """
    audio_path_to_delete: Optional[Path] = None
    
    try:
        meeting = await get_meeting_or_404(meeting_id, db)
        
        # 保存音频文件路径以便后续删除
        if meeting.audio_path:
            audio_path_to_delete = Path(meeting.audio_path)
        
        # 删除会议记录
        await db.delete(meeting)
        await db.commit()
        
        # 删除音频文件（如果存在）
        if audio_path_to_delete and audio_path_to_delete.exists():
            try:
                audio_path_to_delete.unlink()
                logger.info(f"Deleted audio file: {audio_path_to_delete}")
            except Exception as e:
                logger.warning(f"Failed to delete audio file {audio_path_to_delete}: {e}")
        
        return BaseResponse(
            code=0,
            message="会议删除成功"
        )
        
    except MeetingMinutesException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Error deleting meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 9999,
                "message": get_user_friendly_error(e)
            }
        )
