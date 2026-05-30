"""
Smart Copilot REST API 服务

将 Smart Copilot 的所有核心功能封装为可调用的 API 接口。
支持无头模式运行，无需 GUI 环境。

启动方式:
    python smart_copilot_api.py
    
或者使用 uvicorn:
    uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

API 文档:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import os
import sys
import json
import uuid
import tempfile
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# 导入核心模块
from llm_provider import ProviderFactory, load_config, save_config
from ppt_generator import generate_ppt_from_json, extract_json_from_text
from ppt_cocreation import CoCreationDialog
from system_probe_client import SystemProbeClient

# ==========================================
# Pydantic 模型定义
# ==========================================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID（用于多轮对话）")
    system_prompt: Optional[str] = Field("", description="系统提示词")
    stream: bool = Field(False, description="是否使用流式响应")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")

class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str = Field(..., description="会话 ID")
    response: str = Field(..., description="AI 响应")
    timestamp: str = Field(..., description="时间戳")

class PPTGenerateRequest(BaseModel):
    """PPT 生成请求"""
    slides: List[Dict[str, Any]] = Field(..., description="幻灯片数据")
    filename: Optional[str] = Field(None, description="输出文件名")
    theme: Optional[str] = Field("corporate", description="主题样式")

class PPTGenerateResponse(BaseModel):
    """PPT 生成响应"""
    file_path: str = Field(..., description="生成的 PPT 文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    slide_count: int = Field(..., description="幻灯片数量")

class PPTCoCreationRequest(BaseModel):
    """PPT 共创请求"""
    original_text: str = Field(..., description="原始文本")
    slides: List[Dict[str, Any]] = Field(..., description="当前幻灯片数据")
    instruction: str = Field(..., description="修改指令")
    session_id: Optional[str] = Field(None, description="会话 ID")

class TextProcessRequest(BaseModel):
    """文本处理请求"""
    text: str = Field(..., description="待处理文本")
    action: str = Field(..., description="处理类型: translate/polish/explain/summarize/code")
    target_language: Optional[str] = Field("zh", description="目标语言（翻译时使用）")
    custom_instruction: Optional[str] = Field(None, description="自定义指令")

class TextProcessResponse(BaseModel):
    """文本处理响应"""
    original: str = Field(..., description="原始文本")
    processed: str = Field(..., description="处理后文本")
    action: str = Field(..., description="处理类型")

class ConfigRequest(BaseModel):
    """配置请求"""
    provider_type: Optional[str] = Field(None, description="提供者类型: minimax/local")
    minimax_api_key: Optional[str] = Field(None, description="MiniMax API Key")
    local_api_base: Optional[str] = Field(None, description="本地 API 地址")
    local_model: Optional[str] = Field(None, description="本地模型名称")
    local_api_key: Optional[str] = Field(None, description="本地 API Key")

class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    agent_online: bool = Field(..., description="Agent 是否在线")
    broker_online: bool = Field(..., description="Broker 是否在线")
    ide_connected: bool = Field(..., description="IDE 是否连接")
    browser_connected: bool = Field(..., description="浏览器是否连接")
    active_sessions: int = Field(0, description="活跃会话数")

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API 版本")
    uptime: float = Field(..., description="运行时间（秒）")

# ==========================================
# 全局状态管理
# ==========================================

class SessionManager:
    """会话管理器"""
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def get_or_create(self, session_id: Optional[str] = None) -> str:
        if session_id and session_id in self.sessions:
            return session_id
        new_id = session_id or str(uuid.uuid4())
        self.sessions[new_id] = {
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "context": {}
        }
        return new_id
    
    def add_message(self, session_id: str, role: str, content: str):
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_history(self, session_id: str) -> List[Dict]:
        if session_id in self.sessions:
            return self.sessions[session_id]["messages"]
        return []
    
    def get_context(self, session_id: str) -> Dict:
        if session_id in self.sessions:
            return self.sessions[session_id].get("context", {})
        return {}
    
    def update_context(self, session_id: str, context: Dict):
        if session_id in self.sessions:
            self.sessions[session_id]["context"].update(context)

# ==========================================
# FastAPI 应用初始化
# ==========================================

app = FastAPI(
    title="Smart Copilot API",
    description="Smart Copilot 核心功能的 REST API 接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 全局实例
provider = None
session_manager = SessionManager()
probe_client = SystemProbeClient()
start_time = datetime.now()

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global provider
    try:
        provider = ProviderFactory.create_provider()
        print("✅ LLM Provider 初始化成功")
    except Exception as e:
        print(f"⚠️ LLM Provider 初始化失败: {e}")

# ==========================================
# API 端点
# ==========================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "message": "Smart Copilot API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查"""
    uptime = (datetime.now() - start_time).total_seconds()
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        uptime=uptime
    )

# ------------------------------------------
# 聊天接口
# ------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    与 AI 进行对话
    
    支持多轮对话，通过 session_id 维护会话上下文。
    """
    global provider
    
    if not provider:
        raise HTTPException(status_code=500, detail="LLM Provider 未初始化")
    
    session_id = session_manager.get_or_create(request.session_id)
    session_manager.add_message(session_id, "user", request.message)
    
    try:
        # 构建消息历史
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        # 添加历史消息
        history = session_manager.get_history(session_id)
        for msg in history[-10:]:  # 保留最近 10 条
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 获取 AI 响应
        response_text = ""
        for chunk in provider.stream_chat_with_history(messages):
            response_text += chunk
        
        session_manager.add_message(session_id, "assistant", response_text)
        
        return ChatResponse(
            session_id=session_id,
            response=response_text,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 对话失败: {str(e)}")

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口
    
    返回 Server-Sent Events (SSE) 格式的流式响应。
    """
    global provider
    
    if not provider:
        raise HTTPException(status_code=500, detail="LLM Provider 未初始化")
    
    session_id = session_manager.get_or_create(request.session_id)
    session_manager.add_message(session_id, "user", request.message)
    
    async def generate():
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            
            history = session_manager.get_history(session_id)
            for msg in history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            full_response = ""
            for chunk in provider.stream_chat_with_history(messages):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"
            
            session_manager.add_message(session_id, "assistant", full_response)
            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'full_response': full_response})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """获取会话历史"""
    history = session_manager.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "messages": history}

# ------------------------------------------
# PPT 生成接口
# ------------------------------------------

@app.post("/api/ppt/generate", response_model=PPTGenerateResponse)
async def generate_ppt(request: PPTGenerateRequest, background_tasks: BackgroundTasks):
    """
    生成 PPT 文件
    
    根据提供的幻灯片数据生成 PPTX 文件。
    """
    try:
        # 生成文件名
        filename = request.filename or f"ppt_{uuid.uuid4().hex[:8]}.pptx"
        if not filename.endswith('.pptx'):
            filename += '.pptx'
        
        output_path = os.path.join(tempfile.gettempdir(), filename)
        
        # 生成 PPT
        generate_ppt_from_json(request.slides, output_path)
        
        # 获取文件信息
        file_size = os.path.getsize(output_path)
        
        return PPTGenerateResponse(
            file_path=output_path,
            file_size=file_size,
            slide_count=len(request.slides)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 生成失败: {str(e)}")

@app.post("/api/ppt/generate-and-download")
async def generate_and_download_ppt(request: PPTGenerateRequest):
    """
    生成并下载 PPT 文件
    
    生成 PPT 后直接返回文件流供下载。
    """
    try:
        filename = request.filename or f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
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

@app.post("/api/ppt/extract-from-text")
async def extract_ppt_from_text(text: str):
    """
    从文本中提取 PPT 结构
    
    使用 AI 从自然语言文本中提取 PPT 大纲。
    """
    global provider
    
    if not provider:
        raise HTTPException(status_code=500, detail="LLM Provider 未初始化")
    
    try:
        prompt = f"""请将以下文本转换为 PPT 大纲的 JSON 格式。

要求：
1. 输出格式为 JSON 数组
2. 每个元素代表一页幻灯片
3. 包含以下字段：
   - type: "title" 或 "content"
   - title: 幻灯片标题
   - subtitle: 副标题（仅 title 类型）
   - items: 内容要点数组
   - layout: 布局方式（center/text_only/image_right/image_left）

文本内容：
{text}

请直接输出 JSON，不要包含其他说明文字。"""
        
        response = ""
        for chunk in provider.stream_chat(prompt):
            response += chunk
        
        # 提取 JSON
        slides = extract_json_from_text(response)
        
        return {
            "original_text": text,
            "extracted_slides": slides,
            "slide_count": len(slides)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本提取失败: {str(e)}")

@app.post("/api/ppt/cocreation")
async def ppt_cocreation(request: PPTCoCreationRequest):
    """
    PPT 共创接口
    
    根据用户指令修改 PPT 内容。
    """
    global provider
    
    if not provider:
        raise HTTPException(status_code=500, detail="LLM Provider 未初始化")
    
    try:
        session_id = session_manager.get_or_create(request.session_id)
        
        # 构建提示词
        current_slides_json = json.dumps(request.slides, ensure_ascii=False, indent=2)
        
        prompt = f"""你是一个专业的 PPT 设计师。用户想要修改 PPT 内容。

当前 PPT 结构：
{current_slides_json}

用户指令：{request.instruction}

请根据用户指令修改 PPT 结构，输出完整的 JSON 数组格式。
注意：
1. 保持原有的结构规范
2. 只修改用户要求的部分
3. 确保输出是有效的 JSON"""
        
        response = ""
        for chunk in provider.stream_chat(prompt):
            response += chunk
        
        # 提取修改后的幻灯片
        updated_slides = extract_json_from_text(response)
        
        # 更新会话上下文
        session_manager.update_context(session_id, {
            "last_slides": updated_slides,
            "last_instruction": request.instruction
        })
        
        return {
            "session_id": session_id,
            "original_slides": request.slides,
            "updated_slides": updated_slides,
            "instruction": request.instruction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 共创失败: {str(e)}")

# ------------------------------------------
# 文本处理接口
# ------------------------------------------

@app.post("/api/text/process", response_model=TextProcessResponse)
async def process_text(request: TextProcessRequest):
    """
    文本处理接口
    
    支持多种文本处理操作：
    - translate: 翻译
    - polish: 润色
    - explain: 解释
    - summarize: 总结
    - code: 代码解析
    - custom: 自定义处理
    """
    global provider
    
    if not provider:
        raise HTTPException(status_code=500, detail="LLM Provider 未初始化")
    
    # 根据操作类型构建提示词
    prompts = {
        "translate": f"请将以下文本翻译成{'中文' if request.target_language == 'zh' else '英文'}：\n\n{request.text}",
        "polish": f"请润色以下文本，使其更加专业和流畅：\n\n{request.text}",
        "explain": f"请详细解释以下内容：\n\n{request.text}",
        "summarize": f"请总结以下内容的要点：\n\n{request.text}",
        "code": f"请解析以下代码，说明其功能和关键点：\n\n{request.text}"
    }
    
    if request.action == "custom" and request.custom_instruction:
        prompt = f"{request.custom_instruction}\n\n{request.text}"
    elif request.action in prompts:
        prompt = prompts[request.action]
    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作类型: {request.action}")
    
    try:
        response = ""
        for chunk in provider.stream_chat(prompt):
            response += chunk
        
        return TextProcessResponse(
            original=request.text,
            processed=response,
            action=request.action
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本处理失败: {str(e)}")

@app.post("/api/text/translate")
async def translate_text(text: str, target_language: str = "zh"):
    """翻译文本"""
    return await process_text(TextProcessRequest(
        text=text,
        action="translate",
        target_language=target_language
    ))

@app.post("/api/text/polish")
async def polish_text(text: str):
    """润色文本"""
    return await process_text(TextProcessRequest(
        text=text,
        action="polish"
    ))

@app.post("/api/text/explain")
async def explain_text(text: str):
    """解释文本"""
    return await process_text(TextProcessRequest(
        text=text,
        action="explain"
    ))

# ------------------------------------------
# 系统探测接口
# ------------------------------------------

@app.get("/api/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """获取系统状态"""
    broker_online = probe_client.is_broker_alive()
    
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
            front_app = probe_client.get_frontmost_app()
            supported_browsers = ["Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Arc"]
            browser_connected = front_app in supported_browsers
        except:
            pass
    
    return SystemStatusResponse(
        agent_online=broker_online,
        broker_online=broker_online,
        ide_connected=ide_connected,
        browser_connected=browser_connected,
        active_sessions=len(session_manager.sessions)
    )

@app.get("/api/system/clipboard")
async def get_clipboard():
    """获取剪贴板内容"""
    if not probe_client.is_broker_alive():
        raise HTTPException(status_code=503, detail="Broker 服务未运行")
    
    content = probe_client.get_clipboard()
    return {"content": content}

@app.get("/api/system/selection")
async def get_selection():
    """获取当前选中文本"""
    if not probe_client.is_broker_alive():
        raise HTTPException(status_code=503, detail="Broker 服务未运行")
    
    content = probe_client.get_selection()
    return {"content": content}

@app.get("/api/system/frontmost-app")
async def get_frontmost_app():
    """获取当前前台应用"""
    if not probe_client.is_broker_alive():
        raise HTTPException(status_code=503, detail="Broker 服务未运行")
    
    app_name = probe_client.get_frontmost_app()
    return {"app_name": app_name}

@app.get("/api/system/screenshot")
async def get_screenshot():
    """获取前台窗口截图"""
    if not probe_client.is_broker_alive():
        raise HTTPException(status_code=503, detail="Broker 服务未运行")
    
    try:
        image_base64 = probe_client.get_front_window_screenshot()
        return {"image_base64": image_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"截图失败: {str(e)}")

# ------------------------------------------
# 配置管理接口
# ------------------------------------------

@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    config = load_config()
    # 隐藏敏感信息
    safe_config = {
        "provider_type": config.get("provider_type", "minimax"),
        "local_api_base": config.get("local_api_base", ""),
        "local_model": config.get("local_model", ""),
        "has_minimax_key": bool(config.get("minimax_api_key")),
        "has_local_key": bool(config.get("local_api_key"))
    }
    return safe_config

@app.post("/api/config")
async def update_config(request: ConfigRequest):
    """更新配置"""
    global provider
    
    config = load_config()
    
    if request.provider_type:
        config["provider_type"] = request.provider_type
    if request.minimax_api_key:
        config["minimax_api_key"] = request.minimax_api_key
    if request.local_api_base:
        config["local_api_base"] = request.local_api_base
    if request.local_model:
        config["local_model"] = request.local_model
    if request.local_api_key:
        config["local_api_key"] = request.local_api_key
    
    save_config(config)
    
    # 重新初始化 Provider
    try:
        provider = ProviderFactory.create_provider()
        return {"message": "配置已更新，Provider 已重新初始化"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider 初始化失败: {str(e)}")

@app.post("/api/config/scan-models")
async def scan_models(api_base: str = "http://localhost:11434/v1"):
    """扫描可用模型"""
    import httpx
    
    models = []
    error_msg = ""
    
    try:
        with httpx.Client(timeout=5.0, verify=False) as client:
            # 策略 1: 标准 OpenAI 兼容接口
            try:
                response = client.get(f"{api_base}/models")
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        models = [m.get("id") for m in data["data"] if "id" in m]
            except:
                pass
            
            # 策略 2: Ollama 原生接口
            if not models:
                try:
                    base_url = api_base.replace('/v1', '')
                    response = client.get(f"{base_url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        if "models" in data:
                            models = [m.get("name") for m in data["models"] if "name" in m]
                except:
                    pass
    except Exception as e:
        error_msg = f"连接失败: {str(e)}"
    
    return {
        "models": models,
        "error": error_msg,
        "api_base": api_base
    }

# ------------------------------------------
# WebSocket 实时对话接口
# ------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket 实时对话
    
    支持双向实时通信，适合需要低延迟的场景。
    """
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            if "action" not in data:
                await websocket.send_json({"error": "缺少 action 字段"})
                continue
            
            action = data["action"]
            
            if action == "init":
                # 初始化会话
                session_id = session_manager.get_or_create(data.get("session_id"))
                await websocket.send_json({
                    "action": "init",
                    "session_id": session_id,
                    "message": "会话已初始化"
                })
            
            elif action == "chat":
                # 聊天
                if not session_id:
                    session_id = session_manager.get_or_create()
                
                message = data.get("message", "")
                if not message:
                    await websocket.send_json({"error": "消息不能为空"})
                    continue
                
                session_manager.add_message(session_id, "user", message)
                
                # 流式发送响应
                full_response = ""
                for chunk in provider.stream_chat(message):
                    full_response += chunk
                    await websocket.send_json({
                        "action": "chunk",
                        "chunk": chunk,
                        "session_id": session_id
                    })
                
                session_manager.add_message(session_id, "assistant", full_response)
                await websocket.send_json({
                    "action": "done",
                    "session_id": session_id,
                    "full_response": full_response
                })
            
            elif action == "history":
                # 获取历史
                if session_id:
                    history = session_manager.get_history(session_id)
                    await websocket.send_json({
                        "action": "history",
                        "session_id": session_id,
                        "messages": history
                    })
            
            else:
                await websocket.send_json({"error": f"未知 action: {action}"})
    
    except WebSocketDisconnect:
        print(f"WebSocket 断开: {session_id}")
    except Exception as e:
        await websocket.send_json({"error": str(e)})

# ------------------------------------------
# 批量处理接口
# ------------------------------------------

class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    texts: List[str] = Field(..., description="待处理文本列表")
    action: str = Field("translate", description="处理类型")
    target_language: str = Field("zh", description="目标语言")

@app.post("/api/batch/process")
async def batch_process(request: BatchProcessRequest):
    """
    批量文本处理
    
    支持批量翻译、润色等操作。
    """
    results = []
    
    for text in request.texts:
        try:
            result = await process_text(TextProcessRequest(
                text=text,
                action=request.action,
                target_language=request.target_language
            ))
            results.append({
                "original": result.original,
                "processed": result.processed,
                "status": "success"
            })
        except Exception as e:
            results.append({
                "original": text,
                "processed": None,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "action": request.action,
        "total": len(request.texts),
        "success": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results
    }

# ==========================================
# 启动入口
# ==========================================

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 8088))
    print(f"🚀 启动 Smart Copilot API 服务...")
    print(f"📖 API 文档: http://localhost:{port}/docs")
    print(f"📖 ReDoc 文档: http://localhost:{port}/redoc")
    
    uvicorn.run(
        "smart_copilot_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
