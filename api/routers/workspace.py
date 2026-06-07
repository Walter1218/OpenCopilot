"""Workspace 路由：/api/workspace/*

为 v5 Agent Workspace 提供专用 API：
- 最近文件列表
- 任务历史
- 知识/记忆统计摘要
- 文件上传
"""
import os
import json
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

# 工作区数据存储目录
WORKSPACE_DIR = os.path.expanduser("~/.opencopilot/workspace")
RECENT_FILES_PATH = os.path.expanduser("~/.opencopilot/recent_files.json")
MAX_RECENT_FILES = 50


# =============================================================================
# Pydantic 模型
# =============================================================================

class RecentFile(BaseModel):
    """最近文件条目"""
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="完整路径")
    size: int = Field(0, description="文件大小(字节)")
    modified: str = Field("", description="最后修改时间")
    source: str = Field("local", description="来源: local/upload/ide")


class UploadRequest(BaseModel):
    """文件上传请求(file_path 模式)"""
    file_path: str = Field(..., description="源文件路径")
    workspace_dir: Optional[str] = Field(None, description="目标工作区目录")


# =============================================================================
# 端点
# =============================================================================

@router.get("/recent-files")
async def get_recent_files(limit: int = 20):
    """
    获取最近打开的文件列表

    从 ~/.opencopilot/recent_files.json 读取，按修改时间倒序排列。
    """
    print(f"[V5-API] GET /api/workspace/recent-files | limit={limit}")
    try:
        files = []
        if os.path.exists(RECENT_FILES_PATH):
            with open(RECENT_FILES_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            files = raw if isinstance(raw, list) else []
        # 按 modified 倒序
        files.sort(key=lambda x: x.get("modified", ""), reverse=True)
        files = files[:limit]
        print(f"[V5-API] recent-files: returned {len(files)} items")
        return {"files": files, "total": len(files)}
    except Exception as e:
        print(f"[V5-API] recent-files error: {e}")
        raise HTTPException(status_code=500, detail=f"读取最近文件失败: {str(e)}")


@router.get("/task-history")
async def get_task_history(session_id: Optional[str] = None, limit: int = 20):
    """
    获取任务历史

    复用 smart_copilot_api 的 tasks_storage，按创建时间倒序返回。
    """
    print(f"[V5-API] GET /api/workspace/task-history | session_id={session_id}, limit={limit}")
    try:
        from smart_copilot_api import tasks_storage
        tasks = list(tasks_storage.values())
        if session_id:
            tasks = [t for t in tasks if t.get("session_id") == session_id]
        # 按创建时间倒序
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        tasks = tasks[:limit]
        print(f"[V5-API] task-history: returned {len(tasks)} tasks")
        return {"tasks": tasks, "total": len(tasks)}
    except Exception as e:
        print(f"[V5-API] task-history error: {e}")
        raise HTTPException(status_code=500, detail=f"读取任务历史失败: {str(e)}")


@router.get("/memory-stats")
async def get_memory_stats():
    """
    获取知识图谱 / 翻译记忆 / 术语库统计摘要

    聚合多个数据源返回统一统计对象。
    """
    print("[V5-API] GET /api/workspace/memory-stats")
    stats = {
        "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
        "translation_memory": {"entries": 0, "status": "unavailable"},
        "glossary": {"terms": 0, "status": "unavailable"},
    }

    # 知识图谱统计
    try:
        kg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               "knowledge_graph", "opencopilot_knowledge_graph.json")
        if os.path.exists(kg_path):
            with open(kg_path, "r", encoding="utf-8") as f:
                kg_data = json.load(f)
            entities = kg_data.get("entities", [])
            relations = kg_data.get("relations", [])
            stats["knowledge_graph"] = {
                "entities": len(entities),
                "relations": len(relations),
                "status": "ok",
            }
    except Exception as e:
        stats["knowledge_graph"]["status"] = f"error: {e}"

    # 翻译记忆（memory.db 中的 translation 类型）
    try:
        from opencopilot.capabilities.memory.core import MemoryManager
        mm = MemoryManager()
        tm_count = mm.count_memories(memory_type="translation")
        stats["translation_memory"] = {"entries": tm_count, "status": "ok"}
    except Exception:
        pass

    # 术语库（memory.db 中的 glossary 类型）
    try:
        gl_count = mm.count_memories(memory_type="glossary")
        stats["glossary"] = {"terms": gl_count, "status": "ok"}
    except Exception:
        pass

    print(f"[V5-API] memory-stats: kg={stats['knowledge_graph']}, tm={stats['translation_memory']}, gl={stats['glossary']}")
    return stats


@router.post("/upload")
async def upload_file(request: UploadRequest):
    """
    上传文件到工作区

    将指定文件复制到工作区目录 (~/.opencopilot/workspace/)，
    并记录到最近文件列表。
    """
    print(f"[V5-API] POST /api/workspace/upload | file_path={request.file_path}")
    try:
        src = os.path.expanduser(request.file_path)
        if not os.path.exists(src):
            raise HTTPException(status_code=404, detail=f"源文件不存在: {src}")

        # 确保工作区目录存在
        ws_dir = request.workspace_dir or WORKSPACE_DIR
        os.makedirs(ws_dir, exist_ok=True)

        # 复制文件
        filename = os.path.basename(src)
        dst = os.path.join(ws_dir, filename)
        # 避免覆盖：加时间戳
        if os.path.exists(dst):
            base, ext = os.path.splitext(filename)
            dst = os.path.join(ws_dir, f"{base}_{datetime.now().strftime('%H%M%S')}{ext}")

        shutil.copy2(src, dst)
        file_stat = os.stat(dst)

        # 记录到最近文件
        entry = {
            "name": os.path.basename(dst),
            "path": dst,
            "size": file_stat.st_size,
            "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "source": "upload",
        }
        _append_recent_file(entry)

        print(f"[V5-API] upload success: {dst}")
        return {"success": True, "file_path": dst, "name": os.path.basename(dst),
                "size": file_stat.st_size}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[V5-API] upload error: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


# =============================================================================
# 工具函数
# =============================================================================

def _append_recent_file(entry: dict):
    """追加一条最近文件记录"""
    files = []
    if os.path.exists(RECENT_FILES_PATH):
        try:
            with open(RECENT_FILES_PATH, "r", encoding="utf-8") as f:
                files = json.load(f)
            if not isinstance(files, list):
                files = []
        except Exception:
            files = []
    # 去重（按 path）
    files = [f for f in files if f.get("path") != entry.get("path")]
    files.insert(0, entry)
    files = files[:MAX_RECENT_FILES]
    os.makedirs(os.path.dirname(RECENT_FILES_PATH), exist_ok=True)
    with open(RECENT_FILES_PATH, "w", encoding="utf-8") as f:
        json.dump(files, f, ensure_ascii=False, indent=2)
