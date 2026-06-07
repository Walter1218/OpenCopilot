"""配置路由：/api/config"""
import os
import sys
import json
import tempfile
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from smart_copilot_api import ConfigRequest
from llm_provider import load_config, save_config

router = APIRouter(prefix="/api/config", tags=["config"])


# =============================================================================
# Pydantic 模型（v5 新增）
# =============================================================================

class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    provider_type: str = Field(..., description="提供者类型: minimax/local/openai")
    api_base: Optional[str] = Field(None, description="API 地址")
    api_key: Optional[str] = Field(None, description="API Key")
    model: Optional[str] = Field(None, description="模型名称")


class AppearanceConfig(BaseModel):
    """外观配置"""
    theme: Optional[str] = Field(None, description="主题: dark/light/system")
    font_size: Optional[int] = Field(None, description="字体大小")
    language: Optional[str] = Field(None, description="语言: zh/en")


class ShortcutsConfig(BaseModel):
    """快捷键配置"""
    shortcuts: Dict[str, Any] = Field(..., description="快捷键映射")


class ImportRequest(BaseModel):
    """导入配置请求"""
    file_path: str = Field(..., description="配置文件路径")


class ResetRequest(BaseModel):
    """重置配置请求"""
    section: Optional[str] = Field(None, description="要重置的 section，None 表示全部")


@router.get("")
async def get_config():
    return load_config()


@router.post("")
async def update_config(request: ConfigRequest):
    current = load_config()
    updates = request.model_dump(exclude_none=True)
    for k, v in updates.items():
        if isinstance(v, dict):
            current.setdefault(k, {}).update(v)
        else:
            current[k] = v
    save_config(current)
    return {"success": True, "config": current}


@router.post("/scan-models")
async def scan_models():
    """扫描可用模型"""
    try:
        import httpx
        config = load_config()
        base = config.get("local_api_base", "http://localhost:11434/v1")
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{base.rstrip('/')}/models", timeout=5)
            if r.status_code == 200:
                models = r.json().get("data", [])
                return {"models": [m.get("id", m.get("name")) for m in models]}
    except:
        pass
    return {"models": []}


# =============================================================================
# v5 新增端点
# =============================================================================

@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """
    测试 LLM 连接

    对 Cloud LLM 发一个简单的 chat/completions 请求（max_tokens=5），
    对 Local LLM 调 /models 端点验证可达性。
    """
    print(f"[V5-API] POST /api/config/test-connection | provider={request.provider_type}")
    import httpx
    try:
        provider = request.provider_type
        api_base = request.api_base or ""
        api_key = request.api_key or ""
        model = request.model or ""

        if provider in ("minimax", "openai", "cloud"):
            # Cloud LLM: 发一个极小请求
            if not api_base:
                api_base = "https://api.minimax.chat/v1"
            if not model:
                model = "MiniMax-M1"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5,
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                resp = await client.post(
                    f"{api_base.rstrip('/')}/chat/completions",
                    json=payload, headers=headers
                )
                if resp.status_code == 200:
                    print(f"[V5-API] test-connection: cloud OK")
                    return {"success": True, "message": "连接成功", "provider": provider, "model": model}
                else:
                    err = resp.text[:200]
                    print(f"[V5-API] test-connection: cloud FAILED {resp.status_code}")
                    return {"success": False, "message": f"HTTP {resp.status_code}: {err}",
                            "provider": provider}

        elif provider == "local":
            # Local LLM: 检查 /models 端点
            if not api_base:
                api_base = "http://localhost:11434/v1"
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.get(f"{api_base.rstrip('/')}/models")
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    model_list = [m.get("id", m.get("name")) for m in models[:10]]
                    print(f"[V5-API] test-connection: local OK, {len(models)} models")
                    return {"success": True, "message": f"连接成功，发现 {len(models)} 个模型",
                            "provider": provider, "available_models": model_list}
                else:
                    print(f"[V5-API] test-connection: local FAILED {resp.status_code}")
                    return {"success": False, "message": f"HTTP {resp.status_code}", "provider": provider}
        else:
            return {"success": False, "message": f"不支持的 provider 类型: {provider}"}

    except httpx.ConnectError:
        print(f"[V5-API] test-connection: CONNECT_ERROR")
        return {"success": False, "message": "无法连接到目标服务，请检查地址和端口"}
    except httpx.TimeoutException:
        print(f"[V5-API] test-connection: TIMEOUT")
        return {"success": False, "message": "连接超时，请检查网络或服务状态"}
    except Exception as e:
        print(f"[V5-API] test-connection error: {e}")
        raise HTTPException(status_code=500, detail=f"测试连接失败: {str(e)}")


# -----------------------------------------------------------------------------
# Appearance
# -----------------------------------------------------------------------------

@router.get("/appearance")
async def get_appearance():
    """
    获取外观配置

    读取 config.json 中的 appearance section（theme/font_size/language）。
    """
    print("[V5-API] GET /api/config/appearance")
    config = load_config()
    appearance = config.get("appearance", {
        "theme": "dark",
        "font_size": 12,
        "language": "zh",
    })
    return appearance


@router.post("/appearance")
async def save_appearance(request: AppearanceConfig):
    """
    保存外观配置

    将 appearance section 写入 config.json。
    """
    print(f"[V5-API] POST /api/config/appearance | theme={request.theme}")
    try:
        config = load_config()
        if "appearance" not in config:
            config["appearance"] = {}
        updates = request.model_dump(exclude_none=True)
        config["appearance"].update(updates)
        save_config(config)
        print(f"[V5-API] appearance saved: {config['appearance']}")
        return {"success": True, "appearance": config["appearance"]}
    except Exception as e:
        print(f"[V5-API] appearance save error: {e}")
        raise HTTPException(status_code=500, detail=f"保存外观配置失败: {str(e)}")


# -----------------------------------------------------------------------------
# Shortcuts
# -----------------------------------------------------------------------------

SHORTCUT_CONFIG_DIR = os.path.expanduser("~/.opencopilot")
SHORTCUT_CONFIG_FILE = os.path.join(SHORTCUT_CONFIG_DIR, "shortcut_config.json")


@router.get("/shortcuts")
async def get_shortcuts():
    """
    获取快捷键配置

    读取 ~/.opencopilot/shortcut_config.json。
    """
    print("[V5-API] GET /api/config/shortcuts")
    try:
        if os.path.exists(SHORTCUT_CONFIG_FILE):
            with open(SHORTCUT_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[V5-API] shortcuts: loaded {len(data.get('shortcuts', {}))} shortcuts")
            return data
        else:
            # 返回默认快捷键
            from core.shortcut_manager import DEFAULT_SHORTCUTS
            defaults = {"shortcuts": {k: v.to_dict() for k, v in DEFAULT_SHORTCUTS.items()}}
            print(f"[V5-API] shortcuts: returning defaults ({len(defaults['shortcuts'])} items)")
            return defaults
    except Exception as e:
        print(f"[V5-API] shortcuts error: {e}")
        raise HTTPException(status_code=500, detail=f"读取快捷键配置失败: {str(e)}")


@router.post("/shortcuts")
async def save_shortcuts(request: ShortcutsConfig):
    """
    保存快捷键配置

    将快捷键映射写入 ~/.opencopilot/shortcut_config.json。
    """
    print(f"[V5-API] POST /api/config/shortcuts | {len(request.shortcuts)} shortcuts")
    try:
        os.makedirs(SHORTCUT_CONFIG_DIR, exist_ok=True)
        data = {"shortcuts": request.shortcuts}
        with open(SHORTCUT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[V5-API] shortcuts saved")
        return {"success": True, "count": len(request.shortcuts)}
    except Exception as e:
        print(f"[V5-API] shortcuts save error: {e}")
        raise HTTPException(status_code=500, detail=f"保存快捷键配置失败: {str(e)}")


# -----------------------------------------------------------------------------
# Export / Import / Reset
# -----------------------------------------------------------------------------

@router.post("/export")
async def export_config():
    """
    导出当前配置

    将 config.json 复制到临时目录，返回文件路径。
    """
    print("[V5-API] POST /api/config/export")
    try:
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        if not os.path.exists(config_file):
            raise HTTPException(status_code=404, detail="config.json 不存在")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"opencopilot_config_{timestamp}.json"
        export_path = os.path.join(tempfile.gettempdir(), export_name)
        shutil.copy2(config_file, export_path)

        print(f"[V5-API] config exported to {export_path}")
        return {"success": True, "file_path": export_path, "filename": export_name}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[V5-API] export error: {e}")
        raise HTTPException(status_code=500, detail=f"导出配置失败: {str(e)}")


@router.post("/import")
async def import_config(request: ImportRequest):
    """
    导入配置

    从指定 JSON 文件路径导入配置，覆盖当前 config.json。
    """
    print(f"[V5-API] POST /api/config/import | file={request.file_path}")
    try:
        src = os.path.expanduser(request.file_path)
        if not os.path.exists(src):
            raise HTTPException(status_code=404, detail=f"文件不存在: {src}")

        with open(src, "r", encoding="utf-8") as f:
            imported = json.load(f)

        if not isinstance(imported, dict):
            raise HTTPException(status_code=400, detail="配置文件格式错误，应为 JSON 对象")

        save_config(imported)
        print(f"[V5-API] config imported from {src}")
        return {"success": True, "imported_keys": list(imported.keys())}
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON 解析失败")
    except Exception as e:
        print(f"[V5-API] import error: {e}")
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")


@router.post("/reset")
async def reset_config(request: ResetRequest):
    """
    重置配置

    重置指定 section 或全部配置为默认值。
    """
    print(f"[V5-API] POST /api/config/reset | section={request.section}")
    try:
        from config_manager import (
            DEFAULT_AGENT_CONFIG, DEFAULT_LLM_CONFIG,
            DEFAULT_CONCURRENCY_CONFIG, DEFAULT_WEB_SEARCH_CONFIG,
        )
        config = load_config()

        defaults_map = {
            "agent": DEFAULT_AGENT_CONFIG,
            "llm": DEFAULT_LLM_CONFIG,
            "concurrency": DEFAULT_CONCURRENCY_CONFIG,
            "web_search": DEFAULT_WEB_SEARCH_CONFIG,
            "appearance": {"theme": "dark", "font_size": 12, "language": "zh"},
        }

        if request.section:
            if request.section in defaults_map:
                config[request.section] = defaults_map[request.section].copy()
                save_config(config)
                print(f"[V5-API] reset section={request.section}")
                return {"success": True, "reset_section": request.section,
                        "values": config[request.section]}
            else:
                # 直接删除该 section
                if request.section in config:
                    del config[request.section]
                    save_config(config)
                return {"success": True, "reset_section": request.section, "values": {}}
        else:
            # 重置全部：用默认值覆盖所有已知 section
            for section, defaults in defaults_map.items():
                config[section] = defaults.copy()
            save_config(config)
            print(f"[V5-API] reset ALL sections")
            return {"success": True, "reset_sections": list(defaults_map.keys())}
    except Exception as e:
        print(f"[V5-API] reset error: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")
