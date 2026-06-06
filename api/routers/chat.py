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
            from opencopilot.agent.caller import call_agent_pipeline_async
            full = ""
            async for chunk in call_agent_pipeline_async(
                text=request.message,
                action_type=request.persona or "default",
                session_id=session_id,
                context_source=request.context_source or "chat",
                context_meta=request.context or {},
                is_new_task=False,
                enable_web_search=ws.get("enabled", False),
                web_search_force=ws.get("force_search", False),
                timeout=300,
            ):
                full += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"
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


# =============================================================================
# v5 新增端点
# =============================================================================

@router.get("/sessions")
async def list_sessions():
    """
    列出所有聊天会话

    从 SessionManager.sessions 读取，返回会话列表摘要。
    """
    print(f"[V5-API] GET /api/chat/sessions")
    try:
        sessions = []
        for sid, data in session_manager.sessions.items():
            messages = data.get("messages", [])
            last_msg = ""
            if messages:
                last = messages[-1]
                last_msg = last.get("content", "")[:100]
            sessions.append({
                "session_id": sid,
                "created_at": data.get("created_at", ""),
                "message_count": len(messages),
                "last_message": last_msg,
            })
        # 按创建时间倒序
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        print(f"[V5-API] sessions: returned {len(sessions)} sessions")
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        print(f"[V5-API] sessions error: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除指定聊天会话

    从 SessionManager.sessions 中移除指定会话。
    """
    print(f"[V5-API] DELETE /api/chat/sessions/{session_id}")
    try:
        if session_id not in session_manager.sessions:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        del session_manager.sessions[session_id]
        print(f"[V5-API] session {session_id} deleted")
        return {"success": True, "message": f"会话 {session_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[V5-API] delete session error: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


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
