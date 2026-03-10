from openai import AsyncOpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError
from typing import Optional, Dict, Any, AsyncGenerator
import logging
import asyncio
import re

from app.core.config import settings
from app.core.exceptions import (
    LLMServiceError,
    async_retry
)

logger = logging.getLogger(__name__)

# CEO 秘书系统提示词
SYSTEM_PROMPT = """你是一个专业的CEO秘书，专注于整理和生成高质量的会议纪要，确保会议目标和行动计划清晰明确。要保证会议内容被全面地记录、准确地表述。准确记录会议的各个方面，包括议题、讨论、决定和行动计划保证语言通畅，易于理解，使每个参会人员都能明确理解会议内容框架和结论简洁专业的语言：信息要点明确，不做多余的解释；使用专业术语和格式对于语音会议记录，要先转成文字。然后需要你帮忙把转录出来的文本整理成没有口语、逻辑清晰、内容明确的会议纪要

## 工作流程: 
输入: 通过开场白引导用户提供会议讨论的基本信息 
整理: 遵循以下框架来整理用户提供的会议信息，每个步骤后都会进行数据校验确保信息准确性 
会议主题：会议的标题和目的。 
会议日期和时间：会议的具体日期和时间。 
参会人员：列出参加会议的所有人。 
会议记录者：注明记录这些内容的人。 
会议议程：列出会议的所有主题和讨论点。 
主要讨论：详述每个议题的讨论内容，主要包括提出的问题、提议、观点等 
决定和行动计划：列出会议的所有决定，以及计划中要采取的行动，以及负责人和计划完成日期 
下一步打算：列出下一步的计划或在未来的会议中需要讨论的问题 输出: 输出整理后的结构清晰, 描述完整的会议纪要

## 注意: 
整理会议纪要过程中, 需严格遵守信息准确性, 不对用户提供的信息做扩写仅做信息整理, 将一些明显的病句做微调 会议纪要：一份详细记录会议讨论、决定和行动计划的文档。你输出的结果将会直接写入文件并保存，所以请直接输出会议纪要，不要说其他话
因为你得到的是根据音频转录的文本，所以可能会有因为音频模糊、杂音、无关人员讲话出现错别字、无效语句、无关话语，请根据上下文语境判断并修正错误"""


class LLMClient:
    """大模型 API 客户端，用于生成会议纪要"""
    
    def __init__(self, base_url: str, api_key: str, model: str, max_retries: int = 3):
        """
        初始化 LLM 客户端
        
        Args:
            base_url: OpenAI 兼容 API 的基础 URL
            api_key: API 密钥
            model: 使用的模型名称
            max_retries: 最大重试次数，默认 3 次
        """
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model = model
        self.max_retries = max_retries
        logger.info(f"LLMClient initialized with model: {model}, max_retries: {max_retries}")
    
    async def generate_summary(
        self,
        transcript: str,
        title: Optional[str] = None,
        date: Optional[str] = None,
        participants: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        根据会议转录内容生成结构化会议纪要（带重试机制）
        
        Args:
            transcript: 会议转录文本
            title: 会议主题（可选）
            date: 会议时间（可选）
            participants: 参会人员（可选）
            **kwargs: 其他可选参数
            
        Returns:
            生成的会议纪要（Markdown 格式）
            
        Raises:
            LLMServiceError: 当大模型服务调用失败时
        """
        logger.info(f"Generating summary for transcript of length: {len(transcript)}")
        
        prompt = self._build_summary_prompt(
            transcript=transcript,
            title=title,
            date=date,
            participants=participants,
            **kwargs
        )
        
        @async_retry(
            max_attempts=self.max_retries,
            delay=2.0,
            backoff=2.0,
            exceptions=(
                APIConnectionError,
                APITimeoutError,
                RateLimitError,
                asyncio.TimeoutError
            ),
            logger_instance=logger
        )
        async def _do_generate():
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.LLM_TEMPERATURE,
                top_p=settings.LLM_TOP_P,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=120.0,  # 2 分钟超时
                extra_body={
                    "enable_thinking": True,
                    "thinking_budget": settings.LLM_THINKING_BUDGET
                }
            )
            
            summary = response.choices[0].message.content
            if not summary:
                raise LLMServiceError("LLM returned empty response")
            
            # 去除深度思考内容（<think>...</think>）
            summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
            # 处理只有 </think> 没有 <think> 的情况：去除开头至 </think> 的全部内容
            summary = re.sub(r'^.*?</think>', '', summary, flags=re.DOTALL)
            summary = summary.strip()
            if not summary:
                raise LLMServiceError("LLM returned empty response after removing thinking content")
            
            logger.info("Summary generated successfully")
            return summary
        
        try:
            return await _do_generate()
        except RateLimitError as e:
            error_msg = f"LLM API rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError("请求过于频繁，请稍后重试")
        except APITimeoutError as e:
            error_msg = f"LLM API request timed out: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError("服务响应超时，请稍后重试")
        except APIConnectionError as e:
            error_msg = f"Failed to connect to LLM service: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError("无法连接到智能摘要服务")
        except APIError as e:
            error_msg = f"LLM API error: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(f"智能摘要服务错误: {e.message if hasattr(e, 'message') else str(e)}")
        except LLMServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during summary generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMServiceError(error_msg)
    
    async def generate_summary_stream(
        self,
        transcript: str,
        title: Optional[str] = None,
        date: Optional[str] = None,
        participants: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式生成会议纪要，逐个 yield 内容片段
        
        Args:
            transcript: 会议转录文本
            title: 会议主题（可选）
            date: 会议时间（可选）
            participants: 参会人员（可选）
            **kwargs: 其他可选参数
            
        Yields:
            每个 content delta 片段
            
        Raises:
            LLMServiceError: 当大模型服务调用失败时
        """
        logger.info(f"Streaming summary for transcript of length: {len(transcript)}")
        
        prompt = self._build_summary_prompt(
            transcript=transcript,
            title=title,
            date=date,
            participants=participants,
            **kwargs
        )
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.LLM_TEMPERATURE,
                top_p=settings.LLM_TOP_P,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=120.0,
                stream=True,
                extra_body={
                    "enable_thinking": True,
                    "thinking_budget": settings.LLM_THINKING_BUDGET
                }
            )
            
            # 状态机：过滤 <think>...</think> 思考过程
            # think_resolved: True 表示已确定开头是否存在孤立 </think>
            # pre_buf: 在 think_resolved 之前的预缓冲区，用于检测孤立 </think>
            in_thinking = False
            think_resolved = False
            pre_buf = ""
            buf = ""
            OPEN_TAG = "<think>"
            CLOSE_TAG = "</think>"

            async for chunk in stream:
                if not (chunk.choices and len(chunk.choices) > 0):
                    continue
                delta = chunk.choices[0].delta
                if not (delta and delta.content):
                    continue

                if not think_resolved:
                    pre_buf += delta.content
                    open_idx = pre_buf.find(OPEN_TAG)
                    close_idx = pre_buf.find(CLOSE_TAG)

                    if open_idx != -1 and (close_idx == -1 or open_idx <= close_idx):
                        # 正常情况：先遇到 <think>，输出其前面的内容后进入思考过滤
                        think_resolved = True
                        if open_idx > 0:
                            yield pre_buf[:open_idx]
                        in_thinking = True
                        buf = pre_buf[open_idx + len(OPEN_TAG):]
                        pre_buf = ""
                    elif close_idx != -1:
                        # 孤立 </think>：丢弃开头至 </think> 的全部内容
                        think_resolved = True
                        buf = pre_buf[close_idx + len(CLOSE_TAG):]
                        pre_buf = ""
                    else:
                        # 尚未发现任何标签，继续缓冲
                        continue
                else:
                    buf += delta.content

                while buf:
                    if in_thinking:
                        idx = buf.find(CLOSE_TAG)
                        if idx != -1:
                            in_thinking = False
                            buf = buf[idx + len(CLOSE_TAG):]
                        else:
                            # 保留可能是不完整 </think> 前缀的尾部
                            keep = len(CLOSE_TAG) - 1
                            buf = buf[-keep:] if len(buf) > keep else buf
                            break
                    else:
                        idx = buf.find(OPEN_TAG)
                        if idx != -1:
                            # 输出 <think> 之前的内容
                            if idx > 0:
                                yield buf[:idx]
                            in_thinking = True
                            buf = buf[idx + len(OPEN_TAG):]
                        else:
                            # 检查尾部是否可能是 <think> 的不完整前缀
                            safe_len = len(buf)
                            for i in range(1, len(OPEN_TAG)):
                                if buf.endswith(OPEN_TAG[:i]):
                                    safe_len = len(buf) - i
                                    break
                            if safe_len > 0:
                                yield buf[:safe_len]
                            buf = buf[safe_len:]
                            break

            # 流结束处理
            if not think_resolved:
                # 整个流中未出现任何思考标签，直接输出预缓冲内容
                if pre_buf:
                    yield pre_buf
            elif not in_thinking and buf:
                yield buf

            logger.info("Stream summary completed successfully")
            
        except RateLimitError as e:
            error_msg = f"LLM API rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError("请求过于频繁，请稍后重试")
        except APITimeoutError as e:
            error_msg = f"LLM API request timed out: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError("服务响应超时，请稍后重试")
        except APIConnectionError as e:
            error_msg = f"Failed to connect to LLM service: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError("无法连接到智能摘要服务")
        except APIError as e:
            error_msg = f"LLM API error: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(f"智能摘要服务错误: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            error_msg = f"Unexpected error during stream summary: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMServiceError(error_msg)
    
    def _build_summary_prompt(
        self,
        transcript: str,
        title: Optional[str] = None,
        date: Optional[str] = None,
        participants: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        构建会议纪要生成的 Prompt
        
        Args:
            transcript: 会议转录文本
            title: 会议主题
            date: 会议时间
            participants: 参会人员
            **kwargs: 其他参数
            
        Returns:
            完整的 Prompt 文本
        """
        parts = ["请根据以下会议转录内容，整理成结构清晰的会议纪要。\n"]
        meeting_info = []
        if title:
            meeting_info.append(f"会议主题：{title}")
        if date:
            meeting_info.append(f"会议日期和时间：{date}")
        if participants:
            meeting_info.append(f"参会人员：{participants}")
        if meeting_info:
            parts.append("已知的会议信息：\n" + "\n".join(meeting_info) + "\n\n")
        parts.append("会议转录内容：\n")
        parts.append(transcript)
        return "".join(parts)
