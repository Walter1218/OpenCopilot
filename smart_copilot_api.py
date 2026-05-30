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
    
    根据用户指令修改 PPT 内容，支持局部修改和全量修改两种模式。
    
    局部修改返回格式示例：
    - {"action": "update", "slide_index": 0, "field": "title", "value": "新标题"}
    - {"action": "update_item", "slide_index": 0, "item_index": 0, "field": "text", "value": "新内容"}
    - {"action": "add_item", "slide_index": 0, "item": {"text": "新要点", "level": 0}}
    - {"action": "remove_item", "slide_index": 0, "item_index": 0}
    - {"action": "add_slide", "index": 1, "slide": {...}}
    - {"action": "remove_slide", "index": 1}
    """
    global provider
    
    if not provider:
        raise HTTPException(status_code=500, detail="LLM Provider 未初始化")
    
    try:
        session_id = session_manager.get_or_create(request.session_id)
        
        # 构建提示词（支持局部修改）
        current_slides_json = json.dumps(request.slides, ensure_ascii=False, indent=2)
        
        system_prompt = """你是一个 PPT 编辑助手。优先进行局部修改，而不是重新生成整个PPT。

**重要**：不要输出思考过程、推理步骤或解释。只输出修改指令JSON，用 ```json 代码块包裹。如果需要多个操作，用多个代码块分别输出。

修改模式（按优先级排序）：

1. **局部修改**（推荐）：只修改用户指定的部分
   - 修改标题：{"action": "update", "slide_index": 1, "field": "title", "value": "新标题"}
   - 修改副标题：{"action": "update", "slide_index": 0, "field": "subtitle", "value": "新副标题"}
   - 修改版式：{"action": "update", "slide_index": 0, "field": "layout", "value": "image_right"}
   
2. **修改要点**：
   - 更新要点：{"action": "update_item", "slide_index": 1, "item_index": 0, "field": "text", "value": "新内容"}
   - 添加要点：{"action": "add_item", "slide_index": 1, "item": {"text": "新要点", "level": 0, "content_type": "text"}}
   - 删除要点：{"action": "remove_item", "slide_index": 1, "item_index": 0}
   
3. **幻灯片操作**：
   - 添加幻灯片：{"action": "add_slide", "index": 2, "slide": {"title": "新页面", "type": "content", "layout": "text_only", "items": []}}
   - 删除幻灯片：{"action": "remove_slide", "index": 2}

4. **内容转换**（当用户要求转换为图表/表格时）：
   - 转为表格：{"action": "add_item", "slide_index": 0, "item": {"content_type": "table", "table_data": {"title": "标题", "columns": ["列1", "列2"], "rows": [["值1", "值2"]]}}}
   - 转为柱状图：{"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "bar", "chart_data": {"title": "标题", "labels": ["标签1", "标签2"], "datasets": [{"label": "系列", "data": [10, 20], "color": "#007bff"}]}}}
   - 转为折线图：同上，chart_type 改为 "line"
   - 转为饼图：同上，chart_type 改为 "pie"

5. **全局修改**（仅当用户明确要求"重新生成"时使用）：
   - 返回 {"slides": [...]}

内容类型：text / image / flowchart / icon / table / chart
版式类型：center / text_only / image_right / image_left / three_columns / two_columns / full_image"""

        user_message = f"""当前幻灯片数据：
```json
{current_slides_json}
```

用户指令：{request.instruction}

请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）："""

        prompt = f"{system_prompt}\n\n{user_message}"
        
        response = ""
        for chunk in provider.stream_chat(prompt):
            response += chunk
        
        # 解析 AI 响应，支持局部更新和全量更新
        update_data = _parse_cocreation_response(response)
        
        # 判断更新类型
        if "slides" in update_data:
            # 全量更新模式
            update_type = "full"
            action = None
            result = {}
            updated_slides = update_data["slides"]
        elif "action" in update_data or "actions" in update_data:
            # 局部更新模式（支持单个或多个操作）
            update_type = "partial"
            action, result, updated_slides = _execute_cocreation_actions(update_data, request.slides)
        else:
            # 尝试从 response 中提取
            update_type = "full"
            action = None
            result = {}
            updated_slides = extract_json_from_text(response)
        
        # 更新会话上下文
        session_manager.update_context(session_id, {
            "last_slides": updated_slides,
            "last_instruction": request.instruction
        })
        
        return {
            "session_id": session_id,
            "update_type": update_type,
            "original_slides": request.slides if update_type == "full" else None,
            "updated_slides": updated_slides,
            "action": action,
            "action_result": result,
            "raw_response": response,
            "instruction": request.instruction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 共创失败: {str(e)}")


def _parse_cocreation_response(response: str) -> dict:
    """解析 PPT 共创 AI 响应，支持局部更新和全量更新格式
    
    返回格式：
    - 单个操作: {"action": "update", ...}
    - 多个操作: {"actions": [{"action": "update", ...}, {"action": "add_item", ...}]}
    - 全量更新: {"slides": [...]}
    """
    import re
    
    # 移除思考过程（<think>...</think> 或 <think>...</think>）
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # 提取所有 ```json ... ``` 代码块
    code_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
    
    # 如果有多个代码块，尝试解析每个代码块
    if len(code_blocks) > 1:
        actions = []
        for block in code_blocks:
            block = block.strip()
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict) and "action" in parsed:
                    actions.append(parsed)
            except json.JSONDecodeError:
                continue
        
        if len(actions) > 1:
            return {"actions": actions}
        elif len(actions) == 1:
            return actions[0]
    
    # 单个代码块或无代码块的情况
    text = code_blocks[0].strip() if code_blocks else response
    
    # 优先检查数组格式（以 [ 开头）
    start_arr = text.find('[')
    start_obj = text.find('{')
    
    # 如果 [ 出现在 { 之前，先尝试数组格式
    if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        depth = 0
        for idx in range(start_arr, len(text)):
            if text[idx] == '[':
                depth += 1
            elif text[idx] == ']':
                depth -= 1
                if depth == 0:
                    try:
                        return {"slides": json.loads(text[start_arr:idx + 1])}
                    except json.JSONDecodeError:
                        pass
    
    # 尝试对象格式
    if start_obj != -1:
        depth = 0
        for idx in range(start_obj, len(text)):
            if text[idx] == '{':
                depth += 1
            elif text[idx] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start_obj:idx + 1])
                    except json.JSONDecodeError:
                        return {}
    return {}


def _execute_cocreation_actions(update_data: dict, slides: list) -> tuple:
    """执行PPT共创操作，支持单个或多个操作
    
    Returns:
        (action, result, updated_slides)
    """
    # 检查是否是多操作模式
    if "actions" in update_data:
        actions = update_data["actions"]
        results = []
        last_action = None
        
        for action_data in actions:
            action = action_data.get("action")
            result = {}
            
            if action == "update":
                slide_idx = action_data.get("slide_index")
                field = action_data.get("field")
                value = action_data.get("value")
                if 0 <= slide_idx < len(slides) and field:
                    slides[slide_idx][field] = value
                    result = {"updated_field": field, "slide_index": slide_idx}
            
            elif action == "update_item":
                slide_idx = action_data.get("slide_index")
                item_idx = action_data.get("item_index")
                field = action_data.get("field")
                value = action_data.get("value")
                if 0 <= slide_idx < len(slides):
                    items = slides[slide_idx].get("items", [])
                    if 0 <= item_idx < len(items) and field:
                        items[item_idx][field] = value
                        result = {"updated_field": field, "slide_index": slide_idx, "item_index": item_idx}
            
            elif action == "add_item":
                slide_idx = action_data.get("slide_index")
                item = action_data.get("item", {})
                if 0 <= slide_idx < len(slides):
                    slides[slide_idx].setdefault("items", []).append(item)
                    result = {"added_item": item, "slide_index": slide_idx}
            
            elif action == "remove_item":
                slide_idx = action_data.get("slide_index")
                item_idx = action_data.get("item_index")
                if 0 <= slide_idx < len(slides):
                    items = slides[slide_idx].get("items", [])
                    if 0 <= item_idx < len(items):
                        removed = items.pop(item_idx)
                        result = {"removed_item": removed, "slide_index": slide_idx, "item_index": item_idx}
            
            elif action == "add_slide":
                index = action_data.get("index", len(slides))
                slide = action_data.get("slide", {})
                slides.insert(index, slide)
                result = {"added_slide": slide, "index": index}
            
            elif action == "remove_slide":
                index = action_data.get("index")
                if 0 <= index < len(slides):
                    removed = slides.pop(index)
                    result = {"removed_slide": removed, "index": index}
            
            results.append({"action": action, "result": result})
            last_action = action
        
        return last_action, {"multi_actions": results}, slides
    
    # 单个操作模式
    action = update_data.get("action")
    result = {}
    
    if action == "update":
        slide_idx = update_data.get("slide_index")
        field = update_data.get("field")
        value = update_data.get("value")
        if 0 <= slide_idx < len(slides) and field:
            slides[slide_idx][field] = value
            result = {"updated_field": field, "slide_index": slide_idx}
    
    elif action == "update_item":
        slide_idx = update_data.get("slide_index")
        item_idx = update_data.get("item_index")
        field = update_data.get("field")
        value = update_data.get("value")
        if 0 <= slide_idx < len(slides):
            items = slides[slide_idx].get("items", [])
            if 0 <= item_idx < len(items) and field:
                items[item_idx][field] = value
                result = {"updated_field": field, "slide_index": slide_idx, "item_index": item_idx}
    
    elif action == "add_item":
        slide_idx = update_data.get("slide_index")
        item = update_data.get("item", {})
        if 0 <= slide_idx < len(slides):
            slides[slide_idx].setdefault("items", []).append(item)
            result = {"added_item": item, "slide_index": slide_idx}
    
    elif action == "remove_item":
        slide_idx = update_data.get("slide_index")
        item_idx = update_data.get("item_index")
        if 0 <= slide_idx < len(slides):
            items = slides[slide_idx].get("items", [])
            if 0 <= item_idx < len(items):
                removed = items.pop(item_idx)
                result = {"removed_item": removed, "slide_index": slide_idx, "item_index": item_idx}
    
    elif action == "add_slide":
        index = update_data.get("index", len(slides))
        slide = update_data.get("slide", {})
        slides.insert(index, slide)
        result = {"added_slide": slide, "index": index}
    
    elif action == "remove_slide":
        index = update_data.get("index")
        if 0 <= index < len(slides):
            removed = slides.pop(index)
            result = {"removed_slide": removed, "index": index}
    
    return action, result, slides

# ------------------------------------------
# 内容转换接口
# ------------------------------------------

class ContentAnalyzeRequest(BaseModel):
    """内容分析请求"""
    text: str = Field(..., description="待分析文本")

class ContentConvertRequest(BaseModel):
    """内容转换请求"""
    text: str = Field(..., description="待转换文本")
    target_type: str = Field(..., description="目标类型: table/bar/line/pie/flowchart")
    title: Optional[str] = Field("", description="转换后的标题")

@app.post("/api/content/analyze")
async def analyze_content(request: ContentAnalyzeRequest):
    """
    分析文本结构，推荐转换方式
    
    检测文本中的表格、图表、流程图等结构，并返回转换建议。
    """
    try:
        from ppt_cocreation.content_converter import get_conversion_suggestions
        result = get_conversion_suggestions(request.text)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@app.post("/api/content/convert")
async def convert_content(request: ContentConvertRequest):
    """
    将文本转换为图表/表格数据
    
    支持的转换类型：
    - table: 表格
    - bar: 柱状图
    - line: 折线图
    - pie: 饼图
    - flowchart: 流程图
    """
    try:
        from ppt_cocreation.content_converter import ContentConverter
        
        if request.target_type == "table":
            result = ContentConverter.convert_to_table(request.text, request.title)
        elif request.target_type in ("bar", "line", "pie"):
            result = ContentConverter.convert_to_chart(request.text, request.target_type, request.title)
        elif request.target_type == "flowchart":
            result = ContentConverter.convert_to_flowchart(request.text, request.title)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的转换类型: {request.target_type}")
        
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")

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
