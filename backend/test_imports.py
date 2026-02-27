#!/usr/bin/env python3
"""测试模块导入是否正常"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 60)
print("测试模块导入...")
print("=" * 60)

try:
    from app.core.config import settings
    print("✓ app.core.config 导入成功")
except Exception as e:
    print(f"✗ app.core.config 导入失败: {e}")

try:
    from app.core.asr_client import ASRClient
    print("✓ app.core.asr_client 导入成功")
except Exception as e:
    print(f"✗ app.core.asr_client 导入失败: {e}")

try:
    from app.core.llm_client import LLMClient
    print("✓ app.core.llm_client 导入成功")
except Exception as e:
    print(f"✗ app.core.llm_client 导入失败: {e}")

try:
    from app.models.database import Meeting, async_session, init_db
    print("✓ app.models.database 导入成功")
except Exception as e:
    print(f"✗ app.models.database 导入失败: {e}")

try:
    from app.models.schemas import UploadResponse, UploadResponseData
    print("✓ app.models.schemas 导入成功")
except Exception as e:
    print(f"✗ app.models.schemas 导入失败: {e}")

try:
    from app.tasks.processing import MeetingProcessor
    print("✓ app.tasks.processing 导入成功")
except Exception as e:
    print(f"✗ app.tasks.processing 导入失败: {e}")

try:
    from app.api.upload import router
    print("✓ app.api.upload 导入成功")
except Exception as e:
    print(f"✗ app.api.upload 导入失败: {e}")

try:
    from app.main import app
    print("✓ app.main 导入成功")
except Exception as e:
    print(f"✗ app.main 导入失败: {e}")

print("=" * 60)
print("模块导入测试完成!")
print("=" * 60)

# 打印配置信息
print("\n配置信息:")
print(f"  APP_NAME: {settings.APP_NAME}")
print(f"  DEBUG: {settings.DEBUG}")
print(f"  DATABASE_URL: {settings.DATABASE_URL}")
print(f"  ASR_API_URL: {settings.ASR_API_URL}")
print(f"  LLM_MODEL: {settings.LLM_MODEL}")
print(f"  UPLOAD_DIR: {settings.UPLOAD_DIR}")
