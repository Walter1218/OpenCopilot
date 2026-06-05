"""
API Pydantic 模型
=================
从 smart_copilot_api.py 提取，后续路由器从此处导入。
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID")
    system_prompt: Optional[str] = Field("", description="系统提示词")
    stream: bool = Field(False, description="是否流式响应")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    context_source: Optional[str] = Field("chat", description="上下文来源")
    persona: Optional[str] = Field(None, description="人设名称")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    response: str = Field(..., description="AI 响应")
    timestamp: str = Field(..., description="时间戳")


class PPTGenerateRequest(BaseModel):
    slides: List[Dict[str, Any]] = Field(..., description="幻灯片数据")
    filename: Optional[str] = Field(None, description="输出文件名")
    theme: Optional[str] = Field("corporate", description="主题样式")


class PPTGenerateResponse(BaseModel):
    file_path: str = Field(..., description="PPT 文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    slide_count: int = Field(..., description="幻灯片数量")


class TextProcessRequest(BaseModel):
    text: str = Field(..., description="待处理文本")
    action: str = Field(..., description="处理类型")
    target_language: Optional[str] = Field("zh", description="目标语言")
    custom_instruction: Optional[str] = Field(None, description="自定义指令")


class TextProcessResponse(BaseModel):
    original: str = Field(..., description="原始文本")
    processed: str = Field(..., description="处理后文本")
    action: str = Field(..., description="处理类型")


class ConfigRequest(BaseModel):
    provider_type: Optional[str] = Field(None, description="提供者类型")
    minimax_api_key: Optional[str] = Field(None, description="MiniMax API Key")
    local_api_base: Optional[str] = Field(None, description="本地 API 地址")
    local_model: Optional[str] = Field(None, description="本地模型名称")
    agent: Optional[dict] = Field(None, description="Agent 配置")
    llm: Optional[dict] = Field(None, description="LLM 配置")
    concurrency: Optional[dict] = Field(None, description="并发控制")
    web_search: Optional[dict] = Field(None, description="联网搜索")


class SystemStatusResponse(BaseModel):
    agent_online: bool = Field(..., description="Agent 是否在线")
    broker_online: bool = Field(..., description="Broker 是否在线")
    ide_connected: bool = Field(..., description="IDE 是否连接")
    browser_connected: bool = Field(..., description="浏览器是否连接")
    active_sessions: int = Field(0, description="活跃会话数")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API 版本")
    uptime: float = Field(..., description="运行时间（秒）")


class BatchProcessRequest(BaseModel):
    texts: List[str] = Field(..., description="待处理文本列表")
    action: str = Field("translate", description="处理类型")
    target_language: str = Field("zh", description="目标语言")


class SessionListResponse(BaseModel):
    sessions: List[Dict[str, Any]] = Field(..., description="会话列表")
    total: int = Field(..., description="总会话数")


__all__ = [
    "ChatRequest", "ChatResponse",
    "PPTGenerateRequest", "PPTGenerateResponse",
    "TextProcessRequest", "TextProcessResponse",
    "ConfigRequest", "SystemStatusResponse", "HealthCheckResponse",
    "BatchProcessRequest", "SessionListResponse",
]
