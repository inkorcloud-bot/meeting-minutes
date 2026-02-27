from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# ========== 基础响应模型 ==========

class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(0, description="响应码，0表示成功")
    message: str = Field("success", description="响应消息")


class DataResponse(BaseResponse):
    """带数据的响应模型"""
    data: Optional[Any] = Field(None, description="响应数据")


# ========== 上传相关模型 ==========

class UploadRequest(BaseModel):
    """上传请求模型（用于表单数据）"""
    title: str = Field(..., description="会议标题")
    date: Optional[str] = Field(None, description="会议日期")
    participants: Optional[str] = Field(None, description="参会人员")


class UploadResponseData(BaseModel):
    """上传响应数据"""
    meeting_id: str = Field(..., description="会议ID")
    status: str = Field(..., description="当前状态")
    estimated_processing_time: Optional[str] = Field(None, description="预计处理时间")


class UploadResponse(BaseResponse):
    """上传响应"""
    data: UploadResponseData


# ========== 状态查询相关模型 ==========

class StatusResponseData(BaseModel):
    """状态响应数据"""
    meeting_id: str = Field(..., description="会议ID")
    status: str = Field(..., description="当前状态")
    progress: int = Field(..., description="处理进度（0-100）")
    current_step: Optional[str] = Field(None, description="当前步骤")
    error: Optional[str] = Field(None, description="错误信息")


class StatusResponse(BaseResponse):
    """状态响应"""
    data: StatusResponseData


# ========== 会议信息相关模型 ==========

class MeetingResponseData(BaseModel):
    """会议信息响应数据"""
    id: str = Field(..., description="会议ID")
    title: str = Field(..., description="会议标题")
    status: str = Field(..., description="当前状态")
    audio_path: Optional[str] = Field(None, description="音频文件路径")
    audio_duration: Optional[float] = Field(None, description="音频时长（秒）")
    transcript: Optional[str] = Field(None, description="原始转录文本")
    summary: Optional[str] = Field(None, description="生成的纪要（Markdown）")
    progress: int = Field(..., description="处理进度（0-100）")
    current_step: Optional[str] = Field(None, description="当前步骤")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class MeetingResponse(BaseResponse):
    """会议信息响应"""
    data: MeetingResponseData


class MeetingListItem(BaseModel):
    """会议列表项"""
    id: str = Field(..., description="会议ID")
    title: str = Field(..., description="会议标题")
    status: str = Field(..., description="当前状态")
    progress: int = Field(..., description="处理进度（0-100）")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class MeetingListResponseData(BaseModel):
    """会议列表响应数据"""
    total: int = Field(..., description="总数")
    items: list[MeetingListItem] = Field(..., description="会议列表")


class MeetingListResponse(BaseResponse):
    """会议列表响应"""
    data: MeetingListResponseData


# ========== 错误响应模型 ==========

class ErrorResponse(BaseResponse):
    """错误响应"""
    code: int = Field(1, description="错误码")
    message: str = Field(..., description="错误信息")
