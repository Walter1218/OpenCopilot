"""
Smart Copilot 能力平台（已合并到 smart_copilot_api.py）

基于"能力"而非"功能"设计的 API 平台。
核心理念：上下文管理 + 动作执行 + 事件系统

⚠️ 本模块路由已合并到 smart_copilot_api.py，通过 `/platform` 路径访问。
   统一入口: uvicorn smart_copilot_api:app --port 8000
   
   如需单独启动（不推荐）:
       python smart_copilot_platform.py   # 端口 8089
"""

import os
import json
import uuid
import asyncio
import tempfile
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from llm_provider import load_config, save_config
from opencopilot.agent.caller import call_agent_pipeline_async
from ppt_generator import generate_ppt_from_json, extract_json_from_text
from system_probe_client import SystemProbeClient

# 导入 API 注册中心
from api_registry import APIRegistry, create_health_router

# 导入 MCP 客户端
from opencopilot.capabilities.tools.mcp_client import get_mcp_client

# 导入符号分析器
from opencopilot.capabilities.tools.symbol_analyzer import get_symbol_analyzer

# ==========================================
# v4.0: 模型从 platform.models 导入
from platform.models import (
    ContextSource, ActionType, Context, ActionResult,
    ExecuteRequest, ExecuteResponse, ContextResponse,
    ProbeStatusResponse, EventMessage, PPTGenerateRequest,
)

# ==========================================
# 动作执行引擎
# ==========================================

class ActionEngine:
    """动作执行引擎 - 统一的动作执行接口（内嵌 Pipeline 模式）"""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
    
    async def execute(self, request: ExecuteRequest) -> ActionResult:
        """执行动作 - 通过统一 Agent Pipeline 调用器"""
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
        
        session_id = request.session_id or str(uuid.uuid4())
        
        # 调用统一 Agent Pipeline 异步版
        full_result = ""
        try:
            async for chunk in call_agent_pipeline_async(
                text=context.content,
                action_type=request.action.value,
                session_id=session_id,
                context_source=request.context_source.value,
            ):
                full_result += chunk
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent Pipeline 调用失败: {str(e)}")
        
        return ActionResult(
            action=request.action,
            result=full_result,
            context_used=context,
            session_id=session_id
        )
    
    async def execute_stream(self, request: ExecuteRequest):
        """流式执行动作 - 通过统一 Agent Pipeline 调用器"""
        # 获取上下文
        context = await self.context_manager.get_context(
            source=request.context_source,
            content=request.context_content,
            metadata=request.context_metadata
        )
        
        session_id = request.session_id or str(uuid.uuid4())
        full_result = ""
        
        try:
            async for chunk in call_agent_pipeline_async(
                text=context.content,
                action_type=request.action.value,
                session_id=session_id,
                context_source=request.context_source.value,
            ):
                full_result += chunk
                yield {
                    "chunk": chunk,
                    "action": request.action.value,
                    "context_source": context.source.value
                }
        except Exception as e:
            yield {"error": f"Agent Pipeline 调用失败: {str(e)}"}
            return
        
        yield {
            "done": True,
            "full_result": full_result,
            "action": request.action.value,
            "session_id": session_id
        }

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
