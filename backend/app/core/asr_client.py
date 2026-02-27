import httpx
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from app.core.exceptions import (
    ASRServiceError,
    async_retry
)

logger = logging.getLogger(__name__)


class ASRClient:
    """ASR API 客户端，用于调用 FireRedASR2S 进行语音识别"""
    
    def __init__(self, base_url: str, timeout: float = 300.0, max_retries: int = 3):
        """
        初始化 ASR 客户端
        
        Args:
            base_url: ASR API 的基础 URL
            timeout: 请求超时时间（秒），默认 5 分钟
            max_retries: 最大重试次数，默认 3 次
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"ASRClient initialized with base_url: {self.base_url}, max_retries: {max_retries}")
    
    async def transcribe(
        self,
        audio_path: Path,
        enable_vad: bool = True,
        enable_punc: bool = True,
        return_timestamp: bool = True
    ) -> Dict[str, Any]:
        """
        调用 ASR API 进行语音识别（带重试机制）
        
        Args:
            audio_path: 音频文件路径
            enable_vad: 是否启用语音活动检测
            enable_punc: 是否启用标点符号
            return_timestamp: 是否返回时间戳
            
        Returns:
            ASR API 返回的结果
            
        Raises:
            ASRServiceError: 当 ASR 服务调用失败时
            FileNotFoundError: 当音频文件不存在时
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        @async_retry(
            max_attempts=self.max_retries,
            delay=2.0,
            backoff=2.0,
            logger_instance=logger
        )
        async def _do_transcribe():
            url = f"{self.base_url}/system/transcribe"
            logger.info(f"Transcribing audio file: {audio_path}")
            
            with open(audio_path, 'rb') as f:
                files = {'audio': f}
                data = {
                    'enable_vad': str(enable_vad).lower(),
                    'enable_punc': str(enable_punc).lower(),
                    'return_timestamp': str(return_timestamp).lower()
                }
                
                response = await self.client.post(url, files=files, data=data)
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Transcription completed successfully for {audio_path}")
                return result
        
        try:
            return await _do_transcribe()
        except httpx.HTTPStatusError as e:
            error_msg = f"ASR API returned status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"ASR API request timed out after {self.timeout}s"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to ASR service at {self.base_url}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.HTTPError as e:
            error_msg = f"ASR API request failed: {str(e)}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except ASRServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during transcription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ASRServiceError(error_msg)
    
    async def close(self):
        """关闭 HTTP 客户端连接"""
        await self.client.aclose()
        logger.info("ASRClient closed")
    
    async def __aenter__(self):
        """支持 async with 语法"""
        return self
    
    async def submit_job(
        self,
        audio_path: Path,
        enable_vad: bool = True,
        enable_punc: bool = True,
        return_timestamp: bool = True
    ) -> str:
        """
        提交异步转录任务
        
        Args:
            audio_path: 音频文件路径
            enable_vad: 是否启用语音活动检测
            enable_punc: 是否启用标点符号
            return_timestamp: 是否返回时间戳
            
        Returns:
            job_id: 异步任务 ID
            
        Raises:
            ASRServiceError: 当 ASR 服务调用失败时
            FileNotFoundError: 当音频文件不存在时
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        @async_retry(
            max_attempts=self.max_retries,
            delay=2.0,
            backoff=2.0,
            logger_instance=logger
        )
        async def _do_submit():
            url = f"{self.base_url}/system/transcribe/submit"
            logger.info(f"Submitting ASR job for audio file: {audio_path}")
            
            with open(audio_path, 'rb') as f:
                files = {'audio': f}
                data = {
                    'enable_vad': str(enable_vad).lower(),
                    'enable_punc': str(enable_punc).lower(),
                    'return_timestamp': str(return_timestamp).lower()
                }
                
                response = await self.client.post(url, files=files, data=data)
                response.raise_for_status()
                result = response.json()
                
                if 'data' in result and 'job_id' in result['data']:
                    job_id = result['data']['job_id']
                elif 'job_id' in result:
                    job_id = result['job_id']
                else:
                    raise ASRServiceError(f"ASR API response missing job_id: {result}")
                
                logger.info(f"ASR job submitted successfully, job_id: {job_id}")
                return job_id
        
        try:
            return await _do_submit()
        except httpx.HTTPStatusError as e:
            error_msg = f"ASR API returned status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to ASR service at {self.base_url}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.HTTPError as e:
            error_msg = f"ASR API request failed: {str(e)}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except ASRServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during job submission: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ASRServiceError(error_msg)
    
    async def get_job_status(self, job_id: str) -> dict:
        """
        查询异步任务状态
        
        Args:
            job_id: 异步任务 ID
            
        Returns:
            任务状态信息，包含 status 字段 (pending/processing/completed/failed)
            
        Raises:
            ASRServiceError: 当 ASR 服务调用失败时
        """
        @async_retry(
            max_attempts=self.max_retries,
            delay=2.0,
            backoff=2.0,
            logger_instance=logger
        )
        async def _do_get_status():
            url = f"{self.base_url}/system/transcribe/status/{job_id}"
            logger.debug(f"Querying ASR job status: {job_id}")
            
            response = await self.client.get(url)
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"ASR job status for {job_id}: {result}")
            return result
        
        try:
            return await _do_get_status()
        except httpx.HTTPStatusError as e:
            error_msg = f"ASR API returned status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to ASR service at {self.base_url}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.HTTPError as e:
            error_msg = f"ASR API request failed: {str(e)}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during status query: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ASRServiceError(error_msg)
    
    async def get_job_result(self, job_id: str) -> dict:
        """
        获取异步任务结果
        
        Args:
            job_id: 异步任务 ID
            
        Returns:
            完整的转录结果
            
        Raises:
            ASRServiceError: 当 ASR 服务调用失败时
        """
        @async_retry(
            max_attempts=self.max_retries,
            delay=2.0,
            backoff=2.0,
            logger_instance=logger
        )
        async def _do_get_result():
            url = f"{self.base_url}/system/transcribe/result/{job_id}"
            logger.info(f"Fetching ASR job result: {job_id}")
            
            response = await self.client.get(url)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"ASR job result retrieved for {job_id}")
            return result
        
        try:
            return await _do_get_result()
        except httpx.HTTPStatusError as e:
            error_msg = f"ASR API returned status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to ASR service at {self.base_url}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except httpx.HTTPError as e:
            error_msg = f"ASR API request failed: {str(e)}"
            logger.error(error_msg)
            raise ASRServiceError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during result fetch: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ASRServiceError(error_msg)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持 async with 语法，自动关闭连接"""
        await self.close()
