import logging
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends

from app.core.config import settings
from app.core.exceptions import (
    FileValidationError,
    DatabaseError,
    MeetingMinutesException,
    exception_to_http_exception,
    get_user_friendly_error
)
from app.models.database import Meeting, async_session
from app.models.schemas import UploadResponse, UploadResponseData, BaseResponse
from app.tasks.processing import MeetingProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])

# ASR_API 支持的所有音频格式
ALLOWED_AUDIO_EXTENSIONS = frozenset({
    '3gp', '3g2', '8svx', 'aa', 'aac', 'aax', 'ac3', 'act', 'adp', 'adts',
    'adx', 'aif', 'aiff', 'amr', 'ape', 'asf', 'ast', 'au', 'avr', 'caf',
    'cda', 'dff', 'dsf', 'dsm', 'dss', 'dts', 'eac3', 'ec3', 'f32', 'f64',
    'fap', 'flac', 'flv', 'gsm', 'ircam', 'm2ts', 'm4a', 'm4b', 'm4r',
    'mka', 'mkv', 'mp2', 'mp3', 'mp4', 'mpc', 'mpp', 'mts', 'nut', 'nsv',
    'oga', 'ogg', 'oma', 'opus', 'qcp', 'ra', 'ram', 'rm', 'sln', 'smp',
    'snd', 'sox', 'spx', 'tak', 'tta', 'voc', 'w64', 'wav', 'wave', 'webm',
    'wma', 'wve', 'wv', 'xa', 'xwma',
})


def validate_audio_file(audio: UploadFile, content: bytes) -> tuple[str, int]:
    """
    验证音频文件
    
    Args:
        audio: 上传的文件对象
        content: 文件内容
        
    Returns:
        (file_extension, file_size)
        
    Raises:
        FileValidationError: 当文件验证失败时
    """
    # 验证文件类型
    file_ext = audio.filename.split('.')[-1].lower() if '.' in audio.filename else ''
    
    if not file_ext:
        raise FileValidationError("无法识别文件格式，请确保文件名包含扩展名")
    
    if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise FileValidationError(
            f"不支持的文件格式 '{file_ext}'。支持的格式: MP3, WAV, M4A, OGG, FLAC, AAC, OPUS 等共 {len(ALLOWED_AUDIO_EXTENSIONS)} 种"
        )
    
    # 检查文件大小
    file_size = len(content)
    if file_size == 0:
        raise FileValidationError("文件为空")
    
    if file_size > settings.MAX_FILE_SIZE:
        max_size_mb = settings.MAX_FILE_SIZE // (1024 * 1024)
        raise FileValidationError(
            f"文件大小超过限制。当前文件大小: {file_size / (1024*1024):.2f}MB，最大允许: {max_size_mb}MB"
        )
    
    return file_ext, file_size


async def save_meeting_to_database(
    meeting_id: str,
    title: str,
    audio_path: str,
    date: Optional[str] = None,
    participants: Optional[str] = None
):
    """
    保存会议记录到数据库
    
    Args:
        meeting_id: 会议ID
        title: 会议标题
        audio_path: 音频文件路径
        date: 会议日期（可选）
        participants: 参会人员（可选）
        
    Raises:
        DatabaseError: 当数据库操作失败时
    """
    try:
        async with async_session() as session:
            meeting = Meeting(
                id=meeting_id,
                title=title,
                status='uploaded',
                audio_path=str(audio_path),
                progress=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 可选字段：如果数据库模型有这些字段的话
            if hasattr(meeting, 'date') and date:
                meeting.date = date
            if hasattr(meeting, 'participants') and participants:
                meeting.participants = participants
            
            session.add(meeting)
            await session.commit()
            logger.info(f"Meeting record created in database: {meeting_id}")
            
    except Exception as e:
        logger.error(f"Database error while saving meeting: {str(e)}", exc_info=True)
        raise DatabaseError(f"保存会议记录失败: {str(e)}")


async def save_audio_file(
    meeting_id: str,
    filename: str,
    content: bytes
) -> Path:
    """
    保存音频文件到磁盘
    
    Args:
        meeting_id: 会议ID
        filename: 原始文件名
        content: 文件内容
        
    Returns:
        保存的文件路径
        
    Raises:
        FileValidationError: 当文件保存失败时
    """
    try:
        # 确保上传目录存在
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 安全的文件名（防止路径遍历）
        cleaned_filename = filename.replace('/', '_').replace('\\', '_')
        safe_filename = f"{meeting_id}_{cleaned_filename}"
        audio_path = upload_dir / safe_filename
        
        # 写入文件
        with open(audio_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Audio file saved to: {audio_path}")
        return audio_path
        
    except PermissionError as e:
        logger.error(f"Permission error while saving file: {str(e)}")
        raise FileValidationError("没有权限保存文件，请联系管理员")
    except Exception as e:
        logger.error(f"Error while saving file: {str(e)}", exc_info=True)
        raise FileValidationError(f"保存文件失败: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_meeting(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="音频文件"),
    title: str = Form(..., description="会议标题"),
    date: str = Form(None, description="会议日期"),
    participants: str = Form(None, description="参会人员")
):
    """
    上传会议音频并启动异步处理
    
    支持的音频格式: 与 ASR_API 一致，包括 MP3, WAV, M4A, OGG, FLAC, AAC, OPUS 等 70+ 种格式
    
    状态流转: uploaded -> processing -> transcribing -> summarizing -> completed
    """
    audio_path: Optional[Path] = None
    meeting_id: Optional[str] = None
    
    try:
        logger.info(f"Received upload request: title={title}, filename={audio.filename}")
        
        # 验证标题
        if not title or len(title.strip()) == 0:
            raise FileValidationError("会议标题不能为空")
        
        if len(title) > 200:
            raise FileValidationError("会议标题不能超过200个字符")
        
        # 读取文件内容
        content = await audio.read()
        
        # 验证文件
        file_ext, file_size = validate_audio_file(audio, content)
        logger.info(f"File validation passed: ext={file_ext}, size={file_size} bytes")
        
        # 创建会议记录 ID
        meeting_id = str(uuid4())
        logger.info(f"Created meeting_id: {meeting_id}")
        
        # 保存音频文件
        audio_path = await save_audio_file(meeting_id, audio.filename, content)
        
        # 保存到数据库
        await save_meeting_to_database(
            meeting_id=meeting_id,
            title=title.strip(),
            audio_path=str(audio_path),
            date=date,
            participants=participants
        )
        
        # 启动后台处理任务
        processor = MeetingProcessor(meeting_id)
        background_tasks.add_task(processor.process)
        logger.info(f"Background task added for meeting: {meeting_id}")
        
        # 估算处理时间（简单估算：每10分钟音频需要约1分钟处理时间）
        # 这里暂时先固定一个值，后续可以根据音频时长计算
        estimated_time = "15-30分钟"
        
        return UploadResponse(
            code=0,
            message="上传成功，正在处理中",
            data=UploadResponseData(
                meeting_id=meeting_id,
                status="uploaded",
                estimated_processing_time=estimated_time
            )
        )
        
    except MeetingMinutesException as e:
        # 清理已创建的资源
        if audio_path and audio_path.exists():
            try:
                audio_path.unlink()
                logger.info(f"Cleaned up audio file: {audio_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up audio file: {cleanup_error}")
        
        logger.error(f"MeetingMinutesException during upload: {e.message}", exc_info=True)
        raise exception_to_http_exception(e)
        
    except HTTPException:
        # 清理已创建的资源
        if audio_path and audio_path.exists():
            try:
                audio_path.unlink()
                logger.info(f"Cleaned up audio file: {audio_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up audio file: {cleanup_error}")
        
        raise
        
    except Exception as e:
        # 清理已创建的资源
        if audio_path and audio_path.exists():
            try:
                audio_path.unlink()
                logger.info(f"Cleaned up audio file: {audio_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up audio file: {cleanup_error}")
        
        logger.error(f"Unexpected error during upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 9999,
                "message": get_user_friendly_error(e)
            }
        )
