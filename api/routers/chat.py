"""
聊天路由
=======
Chat Router:    /api/chat           POST  非流式聊天
                /api/chat/stream    POST  SSE 流式
                /api/chat/{id}/hist GET   会话历史
WebSocket Router: /ws/chat          WS    实时对话
"""
import json
import asyncio
import os


from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from datetime import datetime

from smart_copilot_api import ChatRequest, ChatResponse
from smart_copilot_api import session_manager, _call_agent_pipeline
from opencopilot.agent import PipelineContext
from llm_provider import load_config

router = APIRouter(prefix="/api/chat", tags=["chat"])
ws_router = APIRouter(tags=["chat-ws"])


# ==========================================
# REST 端点
# ==========================================

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = session_manager.get_or_create(request.session_id)
    session_manager.add_message(session_id, "user", request.message)
    try:
        resp = await _call_agent_pipeline(
            text=request.message, session_id=session_id,
            context_source=request.context_source or "chat",
            context_meta=request.context,
        )
        session_manager.add_message(session_id, "assistant", resp)
        return ChatResponse(session_id=session_id, response=resp, timestamp=datetime.now().isoformat())
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI 对话失败: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    session_id = session_manager.get_or_create(request.session_id)
    session_manager.add_message(session_id, "user", request.message)

    async def generate():
        try:
            config = load_config()
            ws = config.get("web_search", {})
            ctx = PipelineContext(
                request={"text": request.message, "context_source": request.context_source or "chat",
                         "context_meta": request.context or {}, "persona": request.persona},
                session_id=session_id, text=request.message,
                action_type=request.persona or "default",
                enable_web_search=ws.get("enabled", False),
                web_search_force=ws.get("force_search", False),
            )
            import asu_custom_agent
            queue = asyncio.Queue()
            ctx.use_async_queue(queue)
            task = asyncio.create_task(asu_custom_agent.pipeline.execute(ctx))
            full = ""
            while True:
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'error': '管线响应超时'})}\n\n"
                    return
                if line == "data: [DONE]\n\n":
                    break
                if line.startswith("data: "):
                    try:
                        d = json.loads(line[6:])
                        if chunk := d.get("chunk", ""):
                            full += chunk
                            yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"
                    except json.JSONDecodeError:
                        pass
            await task
            session_manager.add_message(session_id, "assistant", full)
            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'full_response': full})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{session_id}/history")
async def get_chat_history(session_id: str):
    history = session_manager.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "messages": history}


# ==========================================
# WebSocket 端点
# ==========================================

@ws_router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    try:
        while True:
            data = await websocket.receive_json()
            if "action" not in data:
                await websocket.send_json({"error": "缺少 action 字段"})
                continue
            action = data["action"]
            if action == "init":
                session_id = session_manager.get_or_create(data.get("session_id"))
                await websocket.send_json({"action": "init", "session_id": session_id, "message": "会话已初始化"})
            elif action == "chat":
                if not session_id:
                    session_id = session_manager.get_or_create()
                msg = data.get("message", "")
                if not msg:
                    await websocket.send_json({"error": "消息不能为空"})
                    continue
                session_manager.add_message(session_id, "user", msg)
                try:
                    resp = await _call_agent_pipeline(text=msg, session_id=session_id, context_source="chat")
                    for i in range(0, len(resp), 20):
                        await websocket.send_json({"action": "chunk", "chunk": resp[i:i+20], "session_id": session_id})
                    session_manager.add_message(session_id, "assistant", resp)
                    await websocket.send_json({"action": "done", "session_id": session_id, "full_response": resp})
                except HTTPException as e:
                    await websocket.send_json({"action": "error", "error": e.detail, "session_id": session_id})
            elif action == "history":
                if session_id:
                    await websocket.send_json({"action": "history", "session_id": session_id,
                                               "messages": session_manager.get_history(session_id)})
            else:
                await websocket.send_json({"error": f"未知 action: {action}"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
