"""能力平台数据模型"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ContextSource(str, Enum):
    IDE = "ide"
    BROWSER = "browser"
    CLIPBOARD = "clipboard"
    SELECTION = "selection"
    FILE = "file"
    CUSTOM = "custom"
    CURRENT = "current"


class ActionType(str, Enum):
    TRANSLATE = "translate"
    POLISH = "polish"
    CODE = "code"
    REVISION = "revision"
    AUTO = "auto"
    EXPLAIN = "explain"
    SUMMARIZE = "summarize"
    CUSTOM = "custom"
    PPT_EXTRACT = "ppt_extract"
    PPT_GENERATE = "ppt_generate"
    PPT_COCREATION = "ppt_cocreation"


@dataclass
class Context:
    source: ContextSource
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ActionResult:
    action: ActionType
    result: str
    context_used: Context
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ExecuteRequest(BaseModel):
    action: ActionType = Field(..., description="动作类型")
    content: str = Field(..., description="待处理内容")
    context_source: ContextSource = Field(ContextSource.CURRENT, description="上下文来源")
    session_id: str = Field(default="default", description="会话 ID")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    custom_instruction: str = Field(default="", description="自定义指令")


class ExecuteResponse(BaseModel):
    success: bool
    action: ActionType
    result: str
    session_id: str
    context_used: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default="", description="时间戳")


class ContextResponse(BaseModel):
    context: Dict[str, Any]
    status: str = "active"


class ProbeStatusResponse(BaseModel):
    broker_alive: bool = False
    accessibility_enabled: bool = False
    screen_recording_enabled: bool = False


class EventMessage(BaseModel):
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default="", description="时间戳")


class PPTGenerateRequest(BaseModel):
    slides: List[Dict[str, Any]] = Field(..., description="幻灯片数据")
    filename: str = Field(default="", description="输出文件名")
    theme: str = Field(default="corporate", description="主题样式")
