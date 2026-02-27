#!/usr/bin/env python3
"""
测试 LLM 客户端
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.llm_client import LLMClient
from app.core.config import settings


async def test_llm_client():
    """测试 LLM 客户端"""
    print("=" * 60)
    print("测试 LLM 客户端")
    print("=" * 60)
    
    # 检查配置
    if not settings.LLM_API_KEY:
        print("⚠️  警告: LLM_API_KEY 未配置")
        print("请在 .env 文件中设置 LLM_API_KEY")
        print("\n当前配置:")
        print(f"  LLM_BASE_URL: {settings.LLM_BASE_URL}")
        print(f"  LLM_MODEL: {settings.LLM_MODEL}")
        print(f"  LLM_API_KEY: {'***' if settings.LLM_API_KEY else '未设置'}")
        return
    
    print(f"配置:")
    print(f"  LLM_BASE_URL: {settings.LLM_BASE_URL}")
    print(f"  LLM_MODEL: {settings.LLM_MODEL}")
    print()
    
    # 创建客户端
    llm_client = LLMClient(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL
    )
    
    # 测试转录内容
    test_transcript = """
    张经理：今天我们来讨论一下新项目的开发计划。首先，我们需要确定项目的时间节点。
    
    李工程师：我建议在三个月内完成第一版，这样可以在年底前上线。
    
    张经理：好的，那就定在12月31日前完成第一版上线。李工，你负责技术架构设计，这周末之前出一个初稿。
    
    李工程师：没问题，我会按时完成。
    
    王产品：关于产品功能，我们需要先做用户调研，了解用户的核心需求。
    
    张经理：对，王产品你负责用户调研，下周五之前提交调研报告。另外，我们还需要准备项目预算，财务那边需要下周三之前拿到。
    
    王产品：好的，我会安排调研工作。预算的话，我和财务那边对接一下。
    
    张经理：好的，那今天的会议就到这里。大家各自按照计划执行，有问题随时沟通。
    """
    
    print("测试转录内容:")
    print("-" * 60)
    print(test_transcript.strip())
    print("-" * 60)
    print()
    
    print("正在生成会议纪要...")
    print()
    
    try:
        # 生成纪要
        summary = await llm_client.generate_summary(
            transcript=test_transcript,
            title="新项目开发计划会议",
            date="2024年1月15日",
            participants="张经理、李工程师、王产品"
        )
        
        print("生成的会议纪要:")
        print("=" * 60)
        print(summary)
        print("=" * 60)
        print()
        print("✅ 测试成功！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_llm_client())
