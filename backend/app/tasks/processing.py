import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.core.asr_client import ASRClient
from app.core.llm_client import LLMClient
from app.core.config import settings
from app.core.exceptions import (
    ASRServiceError,
    LLMServiceError,
    NotFoundError,
    get_user_friendly_error
)
from app.models.database import Meeting, async_session

logger = logging.getLogger(__name__)

# LLM 并发信号量：延迟初始化，在第一次使用时根据配置创建
# 必须在事件循环启动后创建，因此不能在模块加载时直接实例化
_llm_semaphore: Optional[asyncio.Semaphore] = None


def get_llm_semaphore() -> asyncio.Semaphore:
    """获取（或初始化）LLM 并发信号量"""
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(settings.LLM_CONCURRENCY)
        logger.info(f"LLM semaphore initialized with concurrency={settings.LLM_CONCURRENCY}")
    return _llm_semaphore


class MeetingProcessor:
    """会议记录异步处理器"""
    
    def __init__(self, meeting_id: str):
        """
        初始化会议处理器
        
        Args:
            meeting_id: 会议记录 ID
        """
        self.meeting_id = meeting_id
        logger.info(f"MeetingProcessor initialized for meeting_id: {meeting_id}")
    
    async def update_progress(
        self,
        step: str,
        progress: int,
        status: Optional[str] = None,
        error: Optional[str] = None,
        error_details: Optional[str] = None
    ):
        """
        更新会议处理进度
        
        Args:
            step: 当前步骤
            progress: 进度百分比 (0-100)
            status: 状态，如果为 None 则保持原状态或根据 error 推断
            error: 用户友好的错误信息
            error_details: 详细的错误信息（用于调试）
        """
        try:
            async with async_session() as session:
                meeting = await session.get(Meeting, self.meeting_id)
                if meeting:
                    meeting.current_step = step
                    meeting.progress = progress
                    meeting.updated_at = datetime.utcnow()
                    
                    if error:
                        meeting.status = 'failed'
                        meeting.error = error
                        # 如果有详细错误信息，也可以保存到某个字段（这里暂时只记录日志）
                        if error_details:
                            logger.error(f"Meeting {self.meeting_id} error details: {error_details}")
                    elif status:
                        meeting.status = status
                    
                    await session.commit()
                    logger.info(
                        f"Meeting {self.meeting_id} progress updated: "
                        f"step={step}, progress={progress}, status={meeting.status}"
                    )
        except Exception as e:
            logger.error(f"Failed to update progress for meeting {self.meeting_id}: {str(e)}", exc_info=True)
    
    async def get_meeting_info(self) -> tuple[Path, Optional[str], Optional[str], Optional[str]]:
        """
        获取会议信息
        
        Returns:
            (audio_path, title, date, participants)
            
        Raises:
            NotFoundError: 当会议或音频文件不存在时
        """
        async with async_session() as session:
            meeting = await session.get(Meeting, self.meeting_id)
            if not meeting:
                raise NotFoundError(f"会议不存在: {self.meeting_id}")
            
            audio_path = Path(meeting.audio_path)
            if not audio_path.exists():
                raise NotFoundError(f"音频文件不存在: {audio_path}")
            
            return (
                audio_path,
                meeting.title,
                getattr(meeting, 'date', None),
                getattr(meeting, 'participants', None)
            )
    
    async def save_transcript(self, transcript: str):
        """
        保存转录结果
        
        Args:
            transcript: 转录文本
        """
        try:
            async with async_session() as session:
                meeting = await session.get(Meeting, self.meeting_id)
                if meeting:
                    meeting.transcript = transcript
                    meeting.updated_at = datetime.utcnow()
                    await session.commit()
                    logger.info(f"Transcript saved for meeting {self.meeting_id}")
        except Exception as e:
            logger.error(f"Failed to save transcript for meeting {self.meeting_id}: {str(e)}", exc_info=True)
            raise
    
    async def save_asr_job_id(self, job_id: str):
        """
        保存 ASR 任务 ID
        
        Args:
            job_id: ASR 异步任务 ID
        """
        try:
            async with async_session() as session:
                meeting = await session.get(Meeting, self.meeting_id)
                if meeting:
                    meeting.asr_job_id = job_id
                    meeting.updated_at = datetime.utcnow()
                    await session.commit()
                    logger.info(f"ASR job_id saved for meeting {self.meeting_id}: {job_id}")
        except Exception as e:
            logger.error(f"Failed to save ASR job_id for meeting {self.meeting_id}: {str(e)}", exc_info=True)
            raise
    
    async def save_summary(self, summary: str):
        """
        保存会议纪要
        
        Args:
            summary: 生成的会议纪要（Markdown 格式）
        """
        try:
            async with async_session() as session:
                meeting = await session.get(Meeting, self.meeting_id)
                if meeting:
                    meeting.summary = summary
                    meeting.status = 'completed'
                    meeting.progress = 100
                    meeting.current_step = 'completed'
                    meeting.updated_at = datetime.utcnow()
                    await session.commit()
                    logger.info(f"Summary saved and meeting {self.meeting_id} marked as completed")
        except Exception as e:
            logger.error(f"Failed to save summary for meeting {self.meeting_id}: {str(e)}", exc_info=True)
            raise
    
    async def _handle_processing_error(self, step: str, error: Exception) -> str:
        """
        处理处理过程中的错误，生成用户友好的错误信息
        
        Args:
            step: 当前步骤
            error: 异常对象
            
        Returns:
            用户友好的错误信息
        """
        error_details = f"{type(error).__name__}: {str(error)}"
        
        if isinstance(error, NotFoundError):
            user_error = str(error)
        elif isinstance(error, ASRServiceError):
            user_error = f"语音识别失败：{get_user_friendly_error(error)}"
        elif isinstance(error, LLMServiceError):
            user_error = f"智能摘要生成失败：{get_user_friendly_error(error)}"
        elif isinstance(error, FileNotFoundError):
            user_error = "文件不存在，请重新上传"
        elif isinstance(error, asyncio.TimeoutError):
            user_error = "处理超时，请稍后重试"
        else:
            user_error = f"处理失败：{get_user_friendly_error(error)}"
        
        logger.error(
            f"Error in step '{step}' for meeting {self.meeting_id}: {error_details}",
            exc_info=True
        )
        
        return user_error, error_details
    
    async def process(self):
        """
        执行完整的会议处理流程（使用 FireRedASR2S 异步 API）
        
        状态流转：uploaded → processing → transcribing → summarizing → completed
        """
        try:
            logger.info(f"Starting processing for meeting {self.meeting_id}")
            
            # 步骤 0: 开始处理
            await self.update_progress('initializing', 5, status='processing')
            
            # 获取会议信息
            try:
                audio_path, title, date, participants = await self.get_meeting_info()
                logger.info(f"Retrieved meeting info for {self.meeting_id}")
            except Exception as e:
                user_error, error_details = await self._handle_processing_error('initializing', e)
                await self.update_progress('error', 0, error=user_error, error_details=error_details)
                return False
            
            # 步骤 1: 提交 ASR 异步任务
            transcript = None
            try:
                await self.update_progress('submitting-asr', 10)
                logger.info(f"Submitting ASR async job for {self.meeting_id}")
                
                asr_client = ASRClient(settings.ASR_API_URL, max_retries=3)
                
                # 1.1 提交异步任务
                job_id = await asr_client.submit_job(
                    audio_path,
                    enable_vad=True,
                    enable_punc=True,
                    return_timestamp=True
                )
                
                logger.info(f"ASR job submitted for {self.meeting_id}, job_id: {job_id}")
                
                # 1.2 保存 job_id 到数据库
                await self.save_asr_job_id(job_id)
                await self.update_progress('transcribing', 15)
                
                # 1.3 轮询任务状态
                poll_count = 0
                max_polls = settings.ASR_MAX_POLLS
                poll_interval = settings.ASR_POLL_INTERVAL
                
                logger.info(f"Starting ASR job polling for {self.meeting_id}, max_polls={max_polls}, interval={poll_interval}s")
                
                while poll_count < max_polls:
                    # 查询状态
                    status_result = await asr_client.get_job_status(job_id)
                    
                    # 解析状态
                    if 'data' in status_result and 'status' in status_result['data']:
                        status = status_result['data']['status']
                    elif 'status' in status_result:
                        status = status_result['status']
                    else:
                        status = 'unknown'
                    
                    logger.debug(f"ASR job status for {self.meeting_id} (poll {poll_count+1}/{max_polls}): {status}")
                    
                    if status == 'completed':
                        logger.info(f"ASR job completed for {self.meeting_id}")
                        break
                    elif status == 'failed':
                        error_msg = f"ASR task failed: {status_result}"
                        logger.error(error_msg)
                        raise ASRServiceError(error_msg)
                    elif status in ['pending', 'processing']:
                        # 计算进度 (15% - 50%)
                        progress = 15 + min(poll_count * 0.3, 35)
                        await self.update_progress(f'transcribing ({status})', int(progress))
                        await asyncio.sleep(poll_interval)
                        poll_count += 1
                    else:
                        # 未知状态，继续等待
                        progress = 15 + min(poll_count * 0.3, 35)
                        await self.update_progress(f'transcribing (unknown: {status})', int(progress))
                        await asyncio.sleep(poll_interval)
                        poll_count += 1
                
                if poll_count >= max_polls:
                    error_msg = f"ASR job timed out after {max_polls} polls ({max_polls * poll_interval}s)"
                    logger.error(error_msg)
                    raise ASRServiceError(error_msg)
                
                # 1.4 获取转录结果
                await self.update_progress('fetching-result', 50)
                asr_result = await asr_client.get_job_result(job_id)
                
                # 解析转录结果
                if 'data' in asr_result and 'text' in asr_result['data']:
                    transcript = asr_result['data']['text']
                else:
                    transcript = str(asr_result)
                
                logger.info(f"ASR transcription completed for {self.meeting_id}, transcript length: {len(transcript)}")
                
                # 保存转录结果
                await self.save_transcript(transcript)
                await self.update_progress('transcribed', 55)
                
            except Exception as e:
                user_error, error_details = await self._handle_processing_error('transcribing', e)
                await self.update_progress('error', 15, error=user_error, error_details=error_details)
                return False
            
            # 步骤 2: 生成会议纪要（并发受 LLM_CONCURRENCY 限制，超出则排队等待）
            try:
                llm_semaphore = get_llm_semaphore()
                queue_size = settings.LLM_CONCURRENCY - llm_semaphore._value  # noqa: SLF001
                if queue_size >= settings.LLM_CONCURRENCY:
                    logger.info(
                        f"Meeting {self.meeting_id} waiting for LLM slot "
                        f"(concurrency={settings.LLM_CONCURRENCY})"
                    )
                    await self.update_progress('waiting-llm-queue', 60)

                async with llm_semaphore:
                    await self.update_progress('summarizing', 70)
                    logger.info(f"Starting summary generation for {self.meeting_id}")

                    llm_client = LLMClient(
                        settings.LLM_BASE_URL,
                        settings.LLM_API_KEY,
                        settings.LLM_MODEL,
                        max_retries=3
                    )

                    summary_parts = []
                    async for chunk in llm_client.generate_summary_stream(
                        transcript=transcript,
                        title=title,
                        date=date,
                        participants=participants
                    ):
                        summary_parts.append(chunk)
                    summary = "".join(summary_parts)
                    if not summary:
                        raise LLMServiceError("大模型返回空内容")

                    logger.info(f"Summary generation completed for {self.meeting_id}, summary length: {len(summary)}")

                    # 保存纪要并标记完成
                    await self.save_summary(summary)
                    logger.info(f"Processing completed successfully for meeting {self.meeting_id}")

                return True

            except Exception as e:
                user_error, error_details = await self._handle_processing_error('summarizing', e)
                await self.update_progress('error', 70, error=user_error, error_details=error_details)
                return False
            
        except Exception as e:
            # 捕获所有未预期的异常
            user_error, error_details = await self._handle_processing_error('unknown', e)
            try:
                await self.update_progress('error', 0, error=user_error, error_details=error_details)
            except:
                logger.error("Failed to update progress even after error", exc_info=True)
            return False
