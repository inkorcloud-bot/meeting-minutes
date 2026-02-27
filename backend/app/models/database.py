import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Float, Text, Integer, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# 创建异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 创建基类
Base = declarative_base()


class Meeting(Base):
    """会议记录表"""
    
    __tablename__ = "meetings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False, comment="会议标题")
    date = Column(String, nullable=True, comment="会议日期")
    participants = Column(Text, nullable=True, comment="参会人员")
    status = Column(String, nullable=False, default="uploaded", comment="状态")
    audio_path = Column(String, nullable=True, comment="音频文件路径")
    audio_duration = Column(Float, nullable=True, comment="音频时长（秒）")
    transcript = Column(Text, nullable=True, comment="原始转录文本")
    summary = Column(Text, nullable=True, comment="生成的纪要（Markdown）")
    progress = Column(Integer, nullable=False, default=0, comment="处理进度（0-100）")
    current_step = Column(String, nullable=True, comment="当前步骤")
    error = Column(Text, nullable=True, comment="错误信息")
    asr_job_id = Column(String, nullable=True, comment="ASR 异步任务 ID")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    def __repr__(self):
        return f"<Meeting(id={self.id}, title={self.title}, status={self.status})>"


async def init_db():
    """初始化数据库，创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
