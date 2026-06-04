"""
API 应用工厂
============
基底: smart_copilot_api.app，渐进而立的路由模块逐步替代旧路由。
新旧路由共存运行，验证通过后可废弃旧文件。
"""
import os, sys

from smart_copilot_api import app

# 注册所有模块化路由（与旧路由共存）
from api.routers.chat import router as chat_router, ws_router as chat_ws_router
from api.routers.system import router as system_router
from api.routers.file import router as file_router
from api.routers.config import router as config_router
from api.routers.persona import router as persona_router
from api.routers.ppt import router as ppt_router
from api.routers.text import router as text_router
from api.routers.knowledge import router as knowledge_router
from api.routers.coding import router as coding_router
from api.routers.tasks import router as tasks_router
from api.routers.evaluation import router as evaluation_router

app.include_router(chat_router)          # /api/chat/*
app.include_router(chat_ws_router)       # /ws/chat
app.include_router(system_router)        # /api/system/*
app.include_router(file_router)          # /api/file/*
app.include_router(config_router)        # /api/config
app.include_router(persona_router)       # /api/persona/*, /v1/agent/*
app.include_router(ppt_router)           # /api/ppt/*
app.include_router(text_router)          # /api/text/*
app.include_router(knowledge_router)     # /api/knowledge/*
app.include_router(coding_router)        # /api/coding/*
app.include_router(tasks_router)         # /api/tasks/*
app.include_router(evaluation_router)    # /api/evaluation/*

__all__ = ["app"]
