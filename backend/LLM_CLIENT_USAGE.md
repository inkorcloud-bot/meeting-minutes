# LLM 客户端使用指南

## 概述

`LLMClient` 是会议纪要系统的大模型 API 客户端，用于根据会议转录内容生成结构化的会议纪要。

## 快速开始

### 1. 基本使用

```python
from app.core import LLMClient, settings

# 创建客户端实例
llm_client = LLMClient(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    model=settings.LLM_MODEL
)

# 生成会议纪要
summary = await llm_client.generate_summary(
    transcript="会议转录内容...",
    title="项目周会",
    date="2024-01-15",
    participants="张三、李四、王五"
)

print(summary)
```

### 2. 参数说明

`generate_summary` 方法接受以下参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| transcript | str | 是 | 会议转录文本 |
| title | str | 否 | 会议主题 |
| date | str | 否 | 会议时间 |
| participants | str | 否 | 参会人员 |
| **kwargs | Any | 否 | 其他扩展参数 |

### 3. 输出格式

生成的会议纪要包含以下部分：

```markdown
# 会议纪要

## 会议基本信息
- 会议主题：...
- 会议时间：...
- 参会人员：...

## 会议议题
1. 议题1
2. 议题2
...

## 关键讨论点
- 讨论点1
- 讨论点2
...

## 会议决议
- 决议1
- 决议2
...

## 行动项
| 任务 | 负责人 | 截止时间 | 状态 |
|------|--------|----------|------|
| 任务1 | 负责人 | 时间 | 待办 |
...

## 会议总结
一段简洁的总结...
```

## 配置

在 `.env` 文件中配置大模型相关参数：

```env
# 大模型配置
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=deepseek-chat
```

## 测试

运行测试脚本：

```bash
python test_llm_client.py
```

## 注意事项

1. 确保 API 密钥正确配置
2. 转录文本不宜过长，注意 Token 消耗
3. 如遇网络问题，会抛出异常，建议在调用时添加异常处理
