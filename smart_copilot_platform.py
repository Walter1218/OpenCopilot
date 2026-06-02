"""
Smart Copilot 能力平台

基于"能力"而非"功能"设计的 API 平台。
核心理念：上下文管理 + 动作执行 + 事件系统

启动方式:
    python smart_copilot_platform.py
    
API 文档:
    http://localhost:8089/docs
"""

import os
import sys
import json
import uuid
import asyncio
import tempfile
import requests
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from llm_provider import ProviderFactory, ProviderFactoryWithFailover, load_config, save_config
from ppt_generator import generate_ppt_from_json, extract_json_from_text
from system_probe_client import SystemProbeClient

# 导入 API 注册中心
from api_registry import APIRegistry, create_health_router

# 导入 MCP 客户端
from tools.mcp_client import get_mcp_client

# 导入符号分析器
from tools.symbol_analyzer import get_symbol_analyzer

# ==========================================
# 核心数据模型
# ==========================================

class ContextSource(str, Enum):
    """上下文来源"""
    IDE = "ide"
    BROWSER = "browser"
    CLIPBOARD = "clipboard"
    SELECTION = "selection"
    FILE = "file"
    CUSTOM = "custom"
    CURRENT = "current"  # 自动探测当前上下文

class ActionType(str, Enum):
    """动作类型"""
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
    """上下文数据"""
    source: ContextSource
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class ActionResult:
    """动作执行结果"""
    action: ActionType
    result: str
    context_used: Context
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

# ==========================================
# 请求/响应模型
# ==========================================

class ExecuteRequest(BaseModel):
    """统一动作执行请求"""
    action: ActionType = Field(..., description="动作类型")
    context_source: ContextSource = Field(ContextSource.CURRENT, description="上下文来源")
    context_content: Optional[str] = Field(None, description="自定义上下文内容")
    context_metadata: Optional[Dict[str, Any]] = Field(None, description="上下文元数据")
    parameters: Optional[Dict[str, Any]] = Field(None, description="动作参数")
    session_id: Optional[str] = Field(None, description="会话 ID")
    stream: bool = Field(False, description="是否使用流式响应")

class ExecuteResponse(BaseModel):
    """动作执行响应"""
    action: str
    result: str
    context_used: Dict[str, Any]
    session_id: str
    timestamp: str

class ContextResponse(BaseModel):
    """上下文响应"""
    context_id: str
    source: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str

class ProbeStatusResponse(BaseModel):
    """系统探测状态"""
    broker_online: bool
    ide_connected: bool
    browser_connected: bool
    active_sessions: int
    uptime: float

class EventMessage(BaseModel):
    """事件消息"""
    event: str
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==========================================
# 上下文管理器
# ==========================================

class ContextManager:
    """上下文管理器 - 负责获取和管理各种上下文源"""
    
    def __init__(self):
        self.probe_client = SystemProbeClient()
        self._context_history: List[Context] = []
        self._current_context: Optional[Context] = None
    
    async def get_context(self, source: ContextSource, content: Optional[str] = None, 
                         metadata: Optional[Dict[str, Any]] = None) -> Context:
        """获取上下文"""
        
        if source == ContextSource.CUSTOM and content:
            # 使用自定义内容
            context = Context(
                source=ContextSource.CUSTOM,
                content=content,
                metadata=metadata or {}
            )
        elif source == ContextSource.CURRENT:
            # 自动探测当前上下文
            context = await self._probe_current_context()
        elif source == ContextSource.CLIPBOARD:
            context = await self._get_clipboard_context()
        elif source == ContextSource.SELECTION:
            context = await self._get_selection_context()
        elif source == ContextSource.IDE:
            context = await self._get_ide_context()
        elif source == ContextSource.BROWSER:
            context = await self._get_browser_context()
        else:
            raise ValueError(f"不支持的上下文来源: {source}")
        
        # 保存到历史
        self._context_history.append(context)
        self._current_context = context
        
        return context
    
    async def _probe_current_context(self) -> Context:
        """自动探测当前上下文"""
        # 优先级：IDE 选中 > 剪贴板 > 浏览器
        
        # 1. 尝试获取 IDE 选中文本
        ide_context = await self._get_ide_context()
        if ide_context.content:
            return ide_context
        
        # 2. 尝试获取剪贴板
        clipboard_context = await self._get_clipboard_context()
        if clipboard_context.content:
            return clipboard_context
        
        # 3. 尝试获取浏览器内容
        browser_context = await self._get_browser_context()
        if browser_context.content:
            return browser_context
        
        # 4. 返回空上下文
        return Context(
            source=ContextSource.CURRENT,
            content="",
            metadata={"error": "无法自动获取上下文"}
        )
    
    async def _get_clipboard_context(self) -> Context:
        """获取剪贴板上下文"""
        try:
            if not self.probe_client.is_broker_alive():
                return Context(
                    source=ContextSource.CLIPBOARD,
                    content="",
                    metadata={"error": "Broker 服务未运行"}
                )
            
            content = self.probe_client.get_clipboard()
            return Context(
                source=ContextSource.CLIPBOARD,
                content=content or "",
                metadata={"has_content": bool(content)}
            )
        except Exception as e:
            return Context(
                source=ContextSource.CLIPBOARD,
                content="",
                metadata={"error": str(e)}
            )
    
    async def _get_selection_context(self) -> Context:
        """获取选中文本上下文"""
        try:
            if not self.probe_client.is_broker_alive():
                return Context(
                    source=ContextSource.SELECTION,
                    content="",
                    metadata={"error": "Broker 服务未运行"}
                )
            
            content = self.probe_client.get_selection()
            return Context(
                source=ContextSource.SELECTION,
                content=content or "",
                metadata={"has_content": bool(content)}
            )
        except Exception as e:
            return Context(
                source=ContextSource.SELECTION,
                content="",
                metadata={"error": str(e)}
            )
    
    async def _get_ide_context(self) -> Context:
        """获取 IDE 上下文"""
        try:
            import httpx
            # 尝试连接 IDE 扩展
            for port in [31234, 31235, 31236]:
                try:
                    resp = httpx.get(f"http://127.0.0.1:{port}/context", timeout=0.5)
                    if resp.status_code == 200:
                        data = resp.json()
                        return Context(
                            source=ContextSource.IDE,
                            content=data.get("text", ""),
                            metadata={
                                "file_path": data.get("file_path"),
                                "language": data.get("language"),
                                "line_range": data.get("line_range"),
                                "port": port
                            }
                        )
                except:
                    continue
            
            return Context(
                source=ContextSource.IDE,
                content="",
                metadata={"error": "IDE 扩展未连接"}
            )
        except Exception as e:
            return Context(
                source=ContextSource.IDE,
                content="",
                metadata={"error": str(e)}
            )
    
    async def _get_browser_context(self) -> Context:
        """获取浏览器上下文"""
        try:
            if not self.probe_client.is_broker_alive():
                return Context(
                    source=ContextSource.BROWSER,
                    content="",
                    metadata={"error": "Broker 服务未运行"}
                )
            
            # 获取前台应用
            front_app = self.probe_client.get_frontmost_app()
            supported_browsers = ["Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Arc"]
            
            if front_app not in supported_browsers:
                return Context(
                    source=ContextSource.BROWSER,
                    content="",
                    metadata={"error": f"当前应用不是浏览器: {front_app}"}
                )
            
            # 获取浏览器 DOM
            content = self.probe_client.get_browser_dom(front_app)
            return Context(
                source=ContextSource.BROWSER,
                content=content or "",
                metadata={"browser": front_app, "has_content": bool(content)}
            )
        except Exception as e:
            return Context(
                source=ContextSource.BROWSER,
                content="",
                metadata={"error": str(e)}
            )
    
    def get_history(self, limit: int = 10) -> List[Context]:
        """获取上下文历史"""
        return self._context_history[-limit:]
    
    def get_current(self) -> Optional[Context]:
        """获取当前上下文"""
        return self._current_context

# ==========================================
# 动作执行引擎
# ==========================================

class ActionEngine:
    """动作执行引擎 - 统一的动作执行接口"""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.provider = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """初始化 LLM Provider（支持故障转移）"""
        try:
            # 检查是否启用故障转移
            config = load_config()
            failover_enabled = config.get("failover", {}).get("enabled", True)
            
            if failover_enabled:
                self.provider = ProviderFactoryWithFailover.create_provider(use_failover=True)
                print("✅ LLM Provider 初始化成功（故障转移模式）")
            else:
                self.provider = ProviderFactory.create_provider()
                print("✅ LLM Provider 初始化成功（单 Provider 模式）")
        except Exception as e:
            print(f"⚠️ LLM Provider 初始化失败: {e}")
    
    async def execute(self, request: ExecuteRequest) -> ActionResult:
        """执行动作 - 通过 Agent API 统一处理"""
        # 获取上下文
        context = await self.context_manager.get_context(
            source=request.context_source,
            content=request.context_content,
            metadata=request.context_metadata
        )
        
        # 如果上下文为空，抛出异常
        if not context.content and request.context_source != ContextSource.CUSTOM:
            raise HTTPException(
                status_code=400, 
                detail=f"无法获取上下文: {context.metadata.get('error', '内容为空')}"
            )
        
        # 构建 Agent API 请求
        payload = {
            "text": context.content,
            "context_source": request.context_source.value,
            "action_type": request.action.value,
            "session_id": request.session_id or str(uuid.uuid4()),
        }
        
        # 添加参数
        if request.parameters:
            payload["parameters"] = request.parameters
        
        # 调用 Agent API（统一走 persona/context 路径）
        result = await self._call_agent_api(payload)
        
        return ActionResult(
            action=request.action,
            result=result,
            context_used=context,
            session_id=payload["session_id"]
        )
    
    async def execute_stream(self, request: ExecuteRequest):
        """流式执行动作 - 通过 Agent API 统一处理"""
        # 获取上下文
        context = await self.context_manager.get_context(
            source=request.context_source,
            content=request.context_content,
            metadata=request.context_metadata
        )
        
        # 构建 Agent API 请求
        payload = {
            "text": context.content,
            "context_source": request.context_source.value,
            "action_type": request.action.value,
            "session_id": request.session_id or str(uuid.uuid4()),
        }
        
        # 添加参数
        if request.parameters:
            payload["parameters"] = request.parameters
        
        # 调用 Agent API 流式接口
        full_result = ""
        try:
            resp = requests.post(
                "http://127.0.0.1:18888/v1/agent/chat",
                json=payload,
                stream=True,
                timeout=120.0
            )
            
            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            chunk = data_json.get("chunk", "")
                            if chunk:
                                full_result += chunk
                                yield {
                                    "chunk": chunk,
                                    "action": request.action.value,
                                    "context_source": context.source.value
                                }
                        except json.JSONDecodeError:
                            pass
            else:
                error_msg = f"Agent API 返回错误: {resp.status_code}"
                yield {"error": error_msg}
                return
        except Exception as e:
            yield {"error": f"调用 Agent API 失败: {str(e)}"}
            return
        
        yield {
            "done": True,
            "full_result": full_result,
            "action": request.action.value,
            "session_id": payload["session_id"]
        }
    
    async def _call_agent_api(self, payload: Dict[str, Any]) -> str:
        """调用 Agent API - 统一走 persona/context 路径"""
        import re
        try:
            resp = requests.post(
                "http://127.0.0.1:18888/v1/agent/chat",
                json=payload,
                stream=True,
                timeout=120.0
            )
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Agent API 返回错误: {resp.status_code}"
                )
            
            # 解析 SSE 流式响应
            full_text = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data_json = json.loads(data_str)
                        chunk = data_json.get("chunk", "")
                        if chunk:
                            full_text += chunk
                    except json.JSONDecodeError:
                        pass
            
            # 过滤掉 <think>...</think> 标签块
            full_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
            if '<think>' in full_text:
                full_text = full_text.split('<think>')[0]
            
            return full_text.strip()
            
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Agent API 响应超时")
        except requests.exceptions.ConnectionError:
            raise HTTPException(status_code=503, detail="无法连接到 Agent 服务，请确保 Agent 已启动")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"调用 Agent API 失败: {str(e)}")

# ==========================================
# 事件系统
# ==========================================

class EventBus:
    """事件总线 - 支持实时事件订阅和发布"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._websocket_subscribers: Dict[str, List[WebSocket]] = defaultdict(list)
    
    def subscribe(self, event: str, callback: Callable):
        """订阅事件"""
        self._subscribers[event].append(callback)
    
    def subscribe_websocket(self, event: str, websocket: WebSocket):
        """WebSocket 订阅事件"""
        self._websocket_subscribers[event].append(websocket)
    
    def unsubscribe_websocket(self, websocket: WebSocket):
        """取消 WebSocket 订阅"""
        for event in self._websocket_subscribers:
            if websocket in self._websocket_subscribers[event]:
                self._websocket_subscribers[event].remove(websocket)
    
    async def publish(self, event: str, data: Dict[str, Any]):
        """发布事件"""
        message = EventMessage(
            event=event,
            data=data,
            timestamp=datetime.now().isoformat()
        )
        
        # 通知普通订阅者
        for callback in self._subscribers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"事件回调异常: {e}")
        
        # 通知 WebSocket 订阅者
        for ws in self._websocket_subscribers.get(event, []):
            try:
                await ws.send_json(message.dict())
            except:
                pass

# ==========================================
# FastAPI 应用初始化
# ==========================================

app = FastAPI(
    title="Smart Copilot 能力平台",
    description="基于能力设计的 API 平台，支持上下文管理、动作执行和事件系统",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 全局实例
context_manager = ContextManager()
action_engine = ActionEngine(context_manager)
event_bus = EventBus()
start_time = datetime.now()

# API 注册中心
registry = APIRegistry(app)

# MCP 客户端
mcp_client = get_mcp_client()

# 符号分析器
symbol_analyzer = get_symbol_analyzer()

# 立即注册健康检查路由（不依赖 startup 事件）
health_router = create_health_router(registry)
registry.register_module("system", health_router, prefix="", tags=["system"], description="系统健康检查")


def initialize_all_modules():
    """初始化所有模块并注册 API"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 注册健康检查路由
    health_router = create_health_router(registry)
    registry.register_module("system", health_router, prefix="", tags=["system"])
    
    # 尝试导入并注册各个模块
    modules_to_register = [
        ("code_executor", "code_executor.api", "create_executor_router", "/api/executor", "代码执行器"),
        ("security_module", "security_module.api", "create_security_router", "/api/security", "安全模块"),
        ("observability_module", "observability_module.api", "create_observability_router", "/api/observability", "可观测性模块"),
        ("agents_md_module", "agents_md_module.api", "create_immune_router", "/api/agents-md", "AGENTS.md 免疫系统"),
        ("tool_system", "tool_system.api", "create_tool_router", "/api/tools", "工具系统"),
    ]
    
    for module_name, module_path, factory_func_name, prefix, description in modules_to_register:
        try:
            # 动态导入模块
            import importlib
            module = importlib.import_module(module_path)
            
            # 获取工厂函数
            factory_func = getattr(module, factory_func_name)
            
            # 创建路由器（不传入实例，使用默认配置）
            router = factory_func()
            
            # 注册到主系统
            registry.register_module(
                module_name, 
                router, 
                prefix=prefix,
                tags=[module_name],
                description=description
            )
            
            logger.info(f"✅ 已注册模块: {module_name}")
            
        except ImportError as e:
            logger.warning(f"⚠️ 模块 {module_name} 导入失败（可能未安装）: {e}")
        except Exception as e:
            logger.error(f"❌ 注册模块 {module_name} 失败: {e}")
    
    # 打印注册摘要
    registry.print_registration_summary()


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    print("✅ Smart Copilot 能力平台启动")
    
    # 初始化所有模块
    initialize_all_modules()
    
    print(f"✅ 已注册 {len(registry.get_registered_modules())} 个模块")

# ==========================================
# 依赖注入
# ==========================================

async def get_context_manager() -> ContextManager:
    return context_manager

async def get_action_engine() -> ActionEngine:
    return action_engine

async def get_event_bus() -> EventBus:
    return event_bus

# ==========================================
# API 端点
# ==========================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Smart Copilot 能力平台",
        "version": "2.0.0",
        "docs": "/docs",
        "capabilities": ["context", "execute", "probe", "events"]
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    uptime = (datetime.now() - start_time).total_seconds()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "uptime": uptime
    }

# ------------------------------------------
# 上下文管理 API
# ------------------------------------------

@app.get("/api/context/current", response_model=ContextResponse)
async def get_current_context(cm: ContextManager = Depends(get_context_manager)):
    """获取当前上下文"""
    context = cm.get_current()
    if not context:
        raise HTTPException(status_code=404, detail="没有当前上下文")
    
    return ContextResponse(
        context_id=context.context_id,
        source=context.source.value,
        content=context.content,
        metadata=context.metadata,
        timestamp=context.timestamp.isoformat()
    )

@app.post("/api/context/inject", response_model=ContextResponse)
async def inject_context(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    cm: ContextManager = Depends(get_context_manager)
):
    """注入自定义上下文"""
    context = await cm.get_context(
        source=ContextSource.CUSTOM,
        content=content,
        metadata=metadata
    )
    
    return ContextResponse(
        context_id=context.context_id,
        source=context.source.value,
        content=context.content,
        metadata=context.metadata,
        timestamp=context.timestamp.isoformat()
    )

@app.get("/api/context/history")
async def get_context_history(
    limit: int = 10,
    cm: ContextManager = Depends(get_context_manager)
):
    """获取上下文历史"""
    history = cm.get_history(limit)
    return {
        "contexts": [
            {
                "context_id": ctx.context_id,
                "source": ctx.source.value,
                "content": ctx.content[:100] + "..." if len(ctx.content) > 100 else ctx.content,
                "timestamp": ctx.timestamp.isoformat()
            }
            for ctx in history
        ]
    }

# ------------------------------------------
# 动作执行 API
# ------------------------------------------

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_action(
    request: ExecuteRequest,
    engine: ActionEngine = Depends(get_action_engine)
):
    """执行动作"""
    result = await engine.execute(request)
    
    return ExecuteResponse(
        action=result.action.value,
        result=result.result,
        context_used={
            "source": result.context_used.source.value,
            "content_preview": result.context_used.content[:100] + "..." if len(result.context_used.content) > 100 else result.context_used.content
        },
        session_id=result.session_id,
        timestamp=result.timestamp.isoformat()
    )

@app.post("/api/execute/stream")
async def execute_action_stream(
    request: ExecuteRequest,
    engine: ActionEngine = Depends(get_action_engine)
):
    """流式执行动作"""
    async def generate():
        async for chunk in engine.execute_stream(request):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

# ------------------------------------------
# 系统探测 API
# ------------------------------------------

@app.get("/api/probe/status", response_model=ProbeStatusResponse)
async def get_probe_status(cm: ContextManager = Depends(get_context_manager)):
    """获取系统探测状态"""
    broker_online = cm.probe_client.is_broker_alive()
    
    # 检测 IDE 连接
    ide_connected = False
    try:
        import httpx
        for port in [31234, 31235, 31236]:
            try:
                resp = httpx.get(f"http://127.0.0.1:{port}/context", timeout=0.3)
                if resp.status_code in [200, 404]:
                    ide_connected = True
                    break
            except:
                pass
    except:
        pass
    
    # 检测浏览器连接
    browser_connected = False
    if broker_online:
        try:
            front_app = cm.probe_client.get_frontmost_app()
            supported_browsers = ["Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Arc"]
            browser_connected = front_app in supported_browsers
        except:
            pass
    
    return ProbeStatusResponse(
        broker_online=broker_online,
        ide_connected=ide_connected,
        browser_connected=browser_connected,
        active_sessions=0,
        uptime=(datetime.now() - start_time).total_seconds()
    )

@app.get("/api/probe/clipboard")
async def get_clipboard(cm: ContextManager = Depends(get_context_manager)):
    """获取剪贴板内容"""
    context = await cm.get_context(ContextSource.CLIPBOARD)
    return {
        "content": context.content,
        "metadata": context.metadata
    }

@app.get("/api/probe/selection")
async def get_selection(cm: ContextManager = Depends(get_context_manager)):
    """获取选中文本"""
    context = await cm.get_context(ContextSource.SELECTION)
    return {
        "content": context.content,
        "metadata": context.metadata
    }

@app.get("/api/probe/ide/context")
async def get_ide_context(cm: ContextManager = Depends(get_context_manager)):
    """获取 IDE 上下文"""
    context = await cm.get_context(ContextSource.IDE)
    return {
        "content": context.content,
        "metadata": context.metadata
    }

@app.get("/api/probe/browser")
async def get_browser_context(cm: ContextManager = Depends(get_context_manager)):
    """获取浏览器上下文"""
    context = await cm.get_context(ContextSource.BROWSER)
    return {
        "content": context.content,
        "metadata": context.metadata
    }

# ------------------------------------------
# 事件系统 API (WebSocket)
# ------------------------------------------

@app.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    event_bus: EventBus = Depends(get_event_bus)
):
    """WebSocket 事件订阅"""
    await websocket.accept()
    subscribed_events = []
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                events = data.get("events", [])
                for event in events:
                    event_bus.subscribe_websocket(event, websocket)
                    subscribed_events.append(event)
                await websocket.send_json({
                    "action": "subscribed",
                    "events": events
                })
            
            elif action == "unsubscribe":
                events = data.get("events", [])
                for event in events:
                    if event in subscribed_events:
                        subscribed_events.remove(event)
                await websocket.send_json({
                    "action": "unsubscribed",
                    "events": events
                })
            
            elif action == "publish":
                event = data.get("event")
                event_data = data.get("data", {})
                if event:
                    await event_bus.publish(event, event_data)
                    await websocket.send_json({
                        "action": "published",
                        "event": event
                    })
            
            else:
                await websocket.send_json({
                    "error": f"未知 action: {action}"
                })
    
    except WebSocketDisconnect:
        event_bus.unsubscribe_websocket(websocket)
        print(f"WebSocket 断开，取消订阅: {subscribed_events}")
    except Exception as e:
        await websocket.send_json({"error": str(e)})

# ------------------------------------------
# PPT 能力 API
# ------------------------------------------

class PPTGenerateRequest(BaseModel):
    """PPT 生成请求"""
    slides: List[Dict[str, Any]] = Field(..., description="幻灯片数据")
    filename: Optional[str] = Field(None, description="输出文件名")
    theme: Optional[str] = Field("corporate", description="主题样式")

@app.post("/api/ppt/generate")
async def generate_ppt(request: PPTGenerateRequest):
    """生成 PPT 文件"""
    try:
        filename = request.filename or f"ppt_{uuid.uuid4().hex[:8]}.pptx"
        if not filename.endswith('.pptx'):
            filename += '.pptx'
        
        output_path = os.path.join(tempfile.gettempdir(), filename)
        generate_ppt_from_json(request.slides, output_path)
        
        return FileResponse(
            path=output_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 生成失败: {str(e)}")

@app.post("/api/ppt/from-context")
async def generate_ppt_from_context(
    context_source: ContextSource = ContextSource.CURRENT,
    style: str = "corporate",
    cm: ContextManager = Depends(get_context_manager),
    engine: ActionEngine = Depends(get_action_engine)
):
    """从当前上下文生成 PPT"""
    # 获取上下文
    context = await cm.get_context(context_source)
    
    if not context.content:
        raise HTTPException(status_code=400, detail="无法获取上下文内容")
    
    # 提取 PPT 结构
    request = ExecuteRequest(
        action=ActionType.PPT_EXTRACT,
        context_source=ContextSource.CUSTOM,
        context_content=context.content,
        parameters={"style": style}
    )
    
    result = await engine.execute(request)
    slides = json.loads(result.result)
    
    # 生成 PPT
    filename = f"ppt_from_context_{uuid.uuid4().hex[:8]}.pptx"
    output_path = os.path.join(tempfile.gettempdir(), filename)
    generate_ppt_from_json(slides, output_path)
    
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

# ==========================================
# MCP 相关 API 端点
# ==========================================

@app.get("/api/mcp/servers", tags=["mcp"])
async def list_mcp_servers():
    """列出所有配置的 MCP Server"""
    return {
        "servers": mcp_client.list_servers(),
        "count": len(mcp_client.list_servers())
    }


@app.get("/api/mcp/servers/{server_name}/tools", tags=["mcp"])
async def get_mcp_server_tools(server_name: str):
    """获取指定 MCP Server 的工具列表"""
    if server_name not in mcp_client.list_servers():
        raise HTTPException(status_code=404, detail=f"MCP Server '{server_name}' 不存在")
    
    tools = await mcp_client.get_server_tools(server_name)
    return {
        "server": server_name,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema
            }
            for t in tools
        ],
        "count": len(tools)
    }


class MCPCallRequest(BaseModel):
    """MCP 工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


@app.post("/api/mcp/servers/{server_name}/call", tags=["mcp"])
async def call_mcp_tool(server_name: str, request: MCPCallRequest):
    """调用 MCP 工具"""
    if server_name not in mcp_client.list_servers():
        raise HTTPException(status_code=404, detail=f"MCP Server '{server_name}' 不存在")
    
    result = await mcp_client.call_tool(server_name, request.tool_name, request.arguments)
    return {
        "server": server_name,
        "tool": request.tool_name,
        "arguments": request.arguments,
        "success": result.success,
        "result": result.result,
        "error": result.error
    }


@app.post("/api/mcp/refresh", tags=["mcp"])
async def refresh_mcp_config():
    """重新加载 MCP 配置"""
    mcp_client.reload_config()
    return {
        "success": True,
        "servers": mcp_client.list_servers()
    }


@app.get("/api/mcp/status", tags=["mcp"])
async def get_mcp_status():
    """获取 MCP 客户端状态"""
    return mcp_client.get_status()


# ==========================================
# Provider 故障转移相关 API 端点
# ==========================================

@app.get("/api/provider/status", tags=["provider"])
async def get_provider_status():
    """获取 LLM Provider 状态（包括故障转移信息）"""
    try:
        # 获取 ActionEngine 实例
        action_engine = globals().get("action_engine")
        if action_engine and hasattr(action_engine, "provider"):
            provider = action_engine.provider
            
            # 检查是否是故障转移 Provider
            if hasattr(provider, "get_status"):
                return {
                    "success": True,
                    "failover_enabled": True,
                    "status": provider.get_status()
                }
            else:
                return {
                    "success": True,
                    "failover_enabled": False,
                    "provider_type": type(provider).__name__
                }
        else:
            return {
                "success": False,
                "error": "ActionEngine 未初始化"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/provider/failover/test", tags=["provider"])
async def test_failover():
    """测试故障转移功能"""
    try:
        action_engine = globals().get("action_engine")
        if not action_engine or not hasattr(action_engine, "provider"):
            raise HTTPException(status_code=500, detail="ActionEngine 未初始化")
        
        provider = action_engine.provider
        
        # 检查是否是故障转移 Provider
        if not hasattr(provider, "get_status"):
            return {
                "success": True,
                "message": "当前未启用故障转移",
                "failover_enabled": False
            }
        
        # 测试故障转移
        status_before = provider.get_status()
        
        # 模拟故障转移（切换到下一个 Provider）
        if len(provider.providers) > 1:
            provider._switch_to_next()
            status_after = provider.get_status()
            
            return {
                "success": True,
                "message": "故障转移测试成功",
                "failover_enabled": True,
                "status_before": status_before,
                "status_after": status_after
            }
        else:
            return {
                "success": True,
                "message": "只有一个 Provider，无法测试故障转移",
                "failover_enabled": True,
                "status": status_before
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ==========================================
# 符号引用相关 API 端点
# ==========================================

class SymbolReferenceRequest(BaseModel):
    """符号引用请求"""
    file_path: str = Field(..., description="文件路径")
    line: int = Field(..., description="行号 (0-based)")
    character: int = Field(..., description="列号 (0-based)")
    include_declaration: bool = Field(True, description="是否包含声明")


@app.post("/api/code/references", tags=["code"])
async def find_symbol_references(request: SymbolReferenceRequest):
    """查找符号引用"""
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail=f"文件 '{request.file_path}' 不存在")
    
    references = symbol_analyzer.find_references(
        request.file_path,
        request.line,
        request.character,
        request.include_declaration
    )
    
    return {
        "file": request.file_path,
        "position": {
            "line": request.line,
            "character": request.character
        },
        "references": references,
        "count": len(references)
    }


class SymbolDefinitionRequest(BaseModel):
    """符号定义请求"""
    file_path: str = Field(..., description="文件路径")
    line: int = Field(..., description="行号 (0-based)")
    character: int = Field(..., description="列号 (0-based)")


@app.post("/api/code/definition", tags=["code"])
async def find_symbol_definition(request: SymbolDefinitionRequest):
    """查找符号定义"""
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail=f"文件 '{request.file_path}' 不存在")
    
    definition = symbol_analyzer.find_definition(
        request.file_path,
        request.line,
        request.character
    )
    
    return {
        "file": request.file_path,
        "position": {
            "line": request.line,
            "character": request.character
        },
        "definition": definition
    }


@app.get("/api/code/symbols", tags=["code"])
async def get_file_symbols(file_path: str):
    """获取文件符号列表"""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"文件 '{file_path}' 不存在")
    
    symbols = symbol_analyzer.get_document_symbols(file_path)
    
    return {
        "file": file_path,
        "symbols": symbols,
        "count": len(symbols)
    }


@app.post("/api/code/clear-cache", tags=["code"])
async def clear_symbol_cache():
    """清除符号分析缓存"""
    symbol_analyzer.clear_cache()
    return {"success": True, "message": "缓存已清除"}


# ==========================================
# 跨文件符号分析 API 端点
# ==========================================

class ProjectIndexRequest(BaseModel):
    """项目索引请求"""
    project_path: str = Field(..., description="项目路径")
    extensions: List[str] = Field(default=[".py"], description="文件扩展名过滤")


@app.post("/api/code/project/index", tags=["code"])
async def index_project(request: ProjectIndexRequest):
    """索引项目"""
    if not os.path.exists(request.project_path):
        raise HTTPException(status_code=404, detail=f"项目路径 '{request.project_path}' 不存在")
    
    if not os.path.isdir(request.project_path):
        raise HTTPException(status_code=400, detail=f"'{request.project_path}' 不是目录")
    
    indexed_count = symbol_analyzer.index_project(request.project_path, request.extensions)
    
    return {
        "success": True,
        "project_path": request.project_path,
        "indexed_files": indexed_count,
        "extensions": request.extensions
    }


class SymbolSearchRequest(BaseModel):
    """符号搜索请求"""
    name: str = Field(..., description="符号名称")
    symbol_type: Optional[int] = Field(None, description="符号类型（SymbolKind 的值）")


@app.post("/api/code/project/search", tags=["code"])
async def search_symbol_in_project(request: SymbolSearchRequest):
    """在项目中搜索符号"""
    symbols = symbol_analyzer.find_symbol_in_project(request.name, request.symbol_type)
    
    return {
        "success": True,
        "query": request.name,
        "symbol_type": request.symbol_type,
        "symbols": symbols,
        "count": len(symbols)
    }


class ProjectReferencesRequest(BaseModel):
    """项目引用请求"""
    name: str = Field(..., description="符号名称")
    exclude_file: Optional[str] = Field(None, description="排除的文件路径")


@app.post("/api/code/project/references", tags=["code"])
async def find_references_in_project(request: ProjectReferencesRequest):
    """在项目中查找符号引用"""
    references = symbol_analyzer.find_references_in_project(request.name, request.exclude_file)
    
    return {
        "success": True,
        "query": request.name,
        "exclude_file": request.exclude_file,
        "references": references,
        "count": len(references)
    }


@app.get("/api/code/project/symbols", tags=["code"])
async def get_project_symbols():
    """获取项目所有符号"""
    symbols = symbol_analyzer.get_project_symbols()
    
    return {
        "success": True,
        "files": len(symbols),
        "symbols": symbols
    }


@app.get("/api/code/project/statistics", tags=["code"])
async def get_project_statistics():
    """获取项目符号统计信息"""
    stats = symbol_analyzer.get_project_statistics()
    
    return {
        "success": True,
        "statistics": stats
    }


# ==========================================
# 启动入口
# ==========================================

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 8089))
    print(f"🚀 启动 Smart Copilot 能力平台...")
    print(f"📖 API 文档: http://localhost:{port}/docs")
    print(f"📖 ReDoc 文档: http://localhost:{port}/redoc")
    
    uvicorn.run(
        "smart_copilot_platform:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
