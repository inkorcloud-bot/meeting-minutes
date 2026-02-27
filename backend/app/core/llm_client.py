from openai import AsyncOpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError
from typing import Optional, Dict, Any
import logging
import asyncio

from app.core.exceptions import (
    LLMServiceError,
    async_retry
)

logger = logging.getLogger(__name__)


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
                    {
                        "role": "system",
                        "content": "你是一个专业的会议纪要助手，擅长从会议转录中提取关键信息并生成结构化的会议纪要。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000,
                timeout=120.0  # 2 分钟超时
            )
            
            summary = response.choices[0].message.content
            if not summary:
                raise LLMServiceError("LLM returned empty response")
            
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
        # 构建会议基本信息部分
        meeting_info = []
        if title:
            meeting_info.append(f"- 会议主题：{title}")
        else:
            meeting_info.append("- 会议主题：{根据内容推断}")
        
        if date:
            meeting_info.append(f"- 会议时间：{date}")
        else:
            meeting_info.append("- 会议时间：{根据内容推断或留空}")
        
        if participants:
            meeting_info.append(f"- 参会人员：{participants}")
        else:
            meeting_info.append("- 参会人员：{根据内容推断或留空}")
        
        meeting_info_str = "\n".join(meeting_info)
        
        return f"""你是一个专业的会议纪要助手。请根据以下会议转录内容，生成一份结构化的会议纪要。

会议转录内容：
{transcript}

请按以下格式输出 Markdown 格式的会议纪要：

# 会议纪要

## 会议基本信息
{meeting_info_str}

## 会议议题
1. {{议题1}}
2. {{议题2}}
...

## 关键讨论点
- {{讨论点1}}
- {{讨论点2}}
...

## 会议决议
- {{决议1}}
- {{决议2}}
...

## 行动项
| 任务 | 负责人 | 截止时间 | 状态 |
|------|--------|----------|------|
| {{任务1}} | {{负责人}} | {{时间}} | 待办 |
| {{任务2}} | {{负责人}} | {{时间}} | 待办 |
...

## 会议总结
{{一段简洁的总结，50-200字，概括会议的主要内容和成果}}

要求：
1. 确保内容准确、客观，基于转录内容进行总结
2. 如果某些信息无法从转录中推断，可以留空或标注"待定"
3. 行动项要尽可能明确，包含负责人和截止时间（如果有提及）
4. 保持语言简洁、专业
"""
