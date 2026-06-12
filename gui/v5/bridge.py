"""V5Bridge — v5 UI 与后端的桥接层（非 AI 部分）

所有非 AI 操作在此直接调用 Python 模块，不走 HTTP。
AI 操作（explain/fix/polish/chat）仍由 QThread Worker + Agent Pipeline 处理。

命名规则：
    - get_*()  : 获取数据（同步）
    - do_*()   : 执行操作（同步）
    - save_*() : 保存配置（同步）
    - test_*() : 测试连接（可能阻塞，建议异步调用）
"""
import os
import json
import shutil
import subprocess
import tempfile
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# 常量
# =============================================================================

RECENT_FILES_PATH = os.path.expanduser("~/.opencopilot/recent_files.json")
SHORTCUT_CONFIG_DIR = os.path.expanduser("~/.opencopilot")
SHORTCUT_CONFIG_FILE = os.path.join(SHORTCUT_CONFIG_DIR, "shortcut_config.json")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
MAX_RECENT_FILES = 50

# 默认 More 操作列表
DEFAULT_MORE_ACTIONS = [
    {"id": "summarize", "label": "📝 Summarize", "description": "总结内容"},
    {"id": "custom", "label": "✏️ Custom", "description": "自定义指令"},
    {"id": "compare", "label": "🔀 Compare", "description": "对比两段文本"},
    {"id": "extract_keywords", "label": "🏷️ Keywords", "description": "提取关键词"},
    {"id": "generate_test", "label": "🧪 Generate Test", "description": "生成测试用例"},
]


# =============================================================================
# 1. Context Source 数据获取
# =============================================================================

def get_selection_text() -> Dict[str, Any]:
    """获取当前选区文本（通过 Broker SystemProbeClient）"""
    try:
        from system_probe_client import SystemProbeClient
        probe = SystemProbeClient()
        text = probe.get_selection() or ""
        app = probe.get_frontmost_app() or ""
        return {"text": text, "source": "selection", "app_name": app, "status": "ok" if text else "empty"}
    except Exception as e:
        return {"text": "", "source": "selection", "app_name": "", "status": f"error: {e}"}


def get_clipboard_text() -> Dict[str, Any]:
    """获取系统剪贴板内容"""
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
        text = result.stdout
        return {"text": text, "source": "clipboard", "status": "ok" if text else "empty"}
    except Exception as e:
        return {"text": "", "source": "clipboard", "status": f"error: {e}"}


def get_active_document() -> Dict[str, Any]:
    """获取当前活动文档信息（通过 Broker）"""
    try:
        from system_probe_client import SystemProbeClient
        probe = SystemProbeClient()
        app_name = probe.get_frontmost_app() or ""

        doc_info = {
            "app_name": app_name, "file_path": "", "content": "",
            "cursor_line": 0, "line_count": 0, "status": "unavailable",
        }

        try:
            import httpx
            resp = httpx.get(
                "http://127.0.0.1:18889/api/v1/system/active-doc",
                headers=probe.headers, timeout=3.0
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                doc_info.update({
                    "file_path": data.get("file_path", ""),
                    "content": data.get("content", ""),
                    "cursor_line": data.get("cursor_line", 0),
                    "line_count": data.get("line_count", 0),
                    "status": "ok",
                })
        except Exception as e:
            logger.warning(f"get_active_document: IDE doc info failed: {e}")

        return doc_info
    except Exception as e:
        logger.error(f"get_active_document: failed: {e}")
        return {"text": "", "app_name": "", "status": f"error: {e}"}


def get_browser_content() -> Dict[str, Any]:
    """获取浏览器当前标签页内容（通过 Broker）"""
    try:
        from system_probe_client import SystemProbeClient
        probe = SystemProbeClient()

        try:
            dom = probe.get_browser_dom("Chrome")
            return {"text": dom, "source": "browser", "browser": "Chrome", "status": "ok" if dom else "empty"}
        except Exception as e:
            logger.debug(f"get_browser_content: Chrome not available: {e}")
            try:
                dom = probe.get_browser_dom("Safari")
                return {"text": dom, "source": "browser", "browser": "Safari", "status": "ok" if dom else "empty"}
            except Exception as e2:
                logger.debug(f"get_browser_content: Safari not available: {e2}")
                return {"text": "", "source": "browser", "browser": "", "status": "no_browser"}
    except Exception as e:
        logger.error(f"get_browser_content: failed: {e}")
        return {"text": "", "source": "browser", "status": f"error: {e}"}


def get_file_content(file_path: str) -> Dict[str, Any]:
    """读取指定文件内容"""
    try:
        path = os.path.expanduser(file_path)
        if not os.path.exists(path):
            return {"text": "", "file_path": path, "status": "not_found"}

        # Office 文件用 Broker 解析
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.docx', '.pptx'):
            from system_probe_client import SystemProbeClient
            probe = SystemProbeClient()
            result = probe.read_office_file(path)
            return {"text": result.get("content", ""), "file_path": path,
                    "file_type": ext[1:], "status": "ok"}

        # 普通文本文件
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"text": content, "file_path": path,
                "file_size": os.path.getsize(path), "status": "ok"}
    except Exception as e:
        return {"text": "", "file_path": file_path, "status": f"error: {e}"}


def fetch_context(source_id: str, extra: str = "") -> Dict[str, Any]:
    """统一获取指定数据源的上下文内容

    Args:
        source_id: selection / active_doc / browser / clipboard / file
        extra: 附加参数（file 时为文件路径）
    """
    dispatch = {
        "selection": lambda: get_selection_text(),
        "active_doc": lambda: get_active_document(),
        "browser": lambda: get_browser_content(),
        "clipboard": lambda: get_clipboard_text(),
        "file": lambda: get_file_content(extra) if extra else {"text": "", "status": "no_path"},
    }
    fn = dispatch.get(source_id)
    if fn:
        result = fn()
        result.setdefault("source", source_id)
        return result
    return {"text": "", "source": source_id, "status": "unknown_source"}


# =============================================================================
# 2. 操作执行
# =============================================================================

def do_copy_to_clipboard(text: str) -> bool:
    """复制文本到系统剪贴板"""
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(input=text.encode("utf-8"))
        logger.info(f"do_copy_to_clipboard: copied {len(text)} chars")
        return True
    except Exception as e:
        logger.warning(f"do_copy_to_clipboard: failed: {e}")
        return False


def do_apply_to_ide(text: str, action: str = "insert") -> Dict[str, Any]:
    """将文本应用到 IDE（通过 Broker 或降级到剪贴板）"""
    try:
        from system_probe_client import SystemProbeClient
        probe = SystemProbeClient()
        import httpx
        resp = httpx.post(
            "http://127.0.0.1:18889/api/v1/system/insert-text",
            json={"text": text, "action": action, "target": "cursor"},
            headers=probe.headers, timeout=5.0
        )
        if resp.status_code == 200:
            logger.info(f"do_apply_to_ide: broker_insert success, text_len={len(text)}")
            return {"success": True, "method": "broker_insert", "action": action}
    except Exception as e:
        logger.warning(f"do_apply_to_ide: broker insert failed: {e}")

    # 降级到剪贴板
    if do_copy_to_clipboard(text):
        logger.info(f"do_apply_to_ide: fallback to clipboard, text_len={len(text)}")
        return {"success": True, "method": "clipboard", "action": action,
                "message": "已复制到剪贴板，请在 IDE 中 Cmd+V 粘贴"}
    logger.error("do_apply_to_ide: all methods failed")
    return {"success": False, "message": "应用失败"}


def do_export_ppt(slides: list, filename: str = "") -> Dict[str, Any]:
    """导出 PPT 文件（直接调用 ppt_generator）"""
    try:
        from ppt_generator import generate_ppt_from_json
        if not filename:
            filename = f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not filename.endswith('.pptx'):
            filename += '.pptx'
        output_path = os.path.join(tempfile.gettempdir(), filename)
        generate_ppt_from_json(slides, output_path)
        file_size = os.path.getsize(output_path)
        logger.info(f"do_export_ppt: exported {len(slides)} slides to {output_path}")
        return {"success": True, "file_path": output_path, "filename": filename,
                "file_size": file_size, "slide_count": len(slides)}
    except Exception as e:
        logger.error(f"do_export_ppt: failed: {e}")
        return {"success": False, "message": f"PPT 导出失败: {e}"}


def get_more_actions() -> List[Dict]:
    """获取 Work Tab 'More' 按钮的操作列表"""
    try:
        from llm_provider import load_config
        config = load_config()
        custom = config.get("work_actions")
        if custom and isinstance(custom, list):
            return custom
    except Exception as e:
        logger.warning(f"get_more_actions: failed: {e}")
    return DEFAULT_MORE_ACTIONS


# =============================================================================
# 3. 配置管理
# =============================================================================

def get_config() -> Dict[str, Any]:
    """读取完整配置"""
    try:
        from llm_provider import load_config
        return load_config()
    except Exception as e:
        logger.warning(f"get_config: failed: {e}")
        return {}


def save_config(config: Dict[str, Any]) -> bool:
    """保存完整配置"""
    try:
        from llm_provider import save_config as _save
        _save(config)
        return True
    except Exception as e:
        logger.warning(f"save_config: failed: {e}")
        return False


def save_engine_config(provider_type: str, api_key: str = "", model: str = "",
                       api_base: str = "") -> bool:
    """保存引擎配置"""
    try:
        from llm_provider import load_config, save_config as _save
        config = load_config()
        config["provider_type"] = provider_type
        if api_key:
            config[f"{provider_type}_api_key"] = api_key
        if model:
            config[f"{provider_type}_model"] = model
        if api_base:
            config[f"{provider_type}_api_base"] = api_base
        _save(config)
        return True
    except Exception as e:
        logger.warning(f"save_engine_config: failed: {e}")
        return False


def get_agent_runtime_config() -> Dict[str, Any]:
    """获取统一 Agent Runtime 配置"""
    try:
        from config_manager import ConfigManager
        return ConfigManager.get_instance().get_agent_runtime()
    except Exception as e:
        logger.warning(f"get_agent_runtime_config: failed: {e}")
        return {}


def save_agent_runtime_config(
    default_backend: str = "",
    default_provider: str = "",
    default_model: str = "",
    capability_routes: Optional[Dict[str, Any]] = None,
    fallback_policy: Optional[Dict[str, Any]] = None,
) -> bool:
    """保存统一 Agent Runtime 配置"""
    try:
        from llm_provider import load_config, save_config as _save

        config = load_config()
        runtime = config.setdefault("agent_runtime", {})
        if default_backend:
            runtime["default_backend"] = default_backend
        if default_provider:
            runtime["default_provider"] = default_provider
        if default_model:
            runtime["default_model"] = default_model
        if capability_routes is not None:
            runtime["capability_routes"] = capability_routes
        if fallback_policy is not None:
            runtime["fallback_policy"] = fallback_policy
        _save(config)
        return True
    except Exception as e:
        logger.warning(f"save_agent_runtime_config: failed: {e}")
        return False


def test_llm_connection(provider_type: str, api_base: str = "",
                        api_key: str = "", model: str = "") -> Dict[str, Any]:
    """测试 LLM 连接（阻塞操作，建议在 QThread 中调用）"""
    import httpx
    try:
        if provider_type in ("minimax", "openai", "cloud"):
            base = api_base or "https://api.minimax.chat/v1"
            mdl = model or "MiniMax-M1"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": mdl, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
            resp = httpx.post(f"{base.rstrip('/')}/chat/completions",
                              json=payload, headers=headers, timeout=15.0)
            if resp.status_code == 200:
                return {"success": True, "message": "连接成功", "model": mdl}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif provider_type == "local":
            base = api_base or "http://localhost:11434/v1"
            resp = httpx.get(f"{base.rstrip('/')}/models", timeout=10.0)
            if resp.status_code == 200:
                models = [m.get("id", "") for m in resp.json().get("data", [])[:10]]
                return {"success": True, "message": f"发现 {len(models)} 个模型", "models": models}
            return {"success": False, "message": f"HTTP {resp.status_code}"}

        return {"success": False, "message": f"不支持的 provider: {provider_type}"}
    except httpx.ConnectError:
        return {"success": False, "message": "无法连接到目标服务"}
    except httpx.TimeoutException:
        return {"success": False, "message": "连接超时"}
    except Exception as e:
        logger.warning(f"test_llm_connection: failed: {e}")
        return {"success": False, "message": str(e)}


# --- Appearance ---

def get_appearance() -> Dict[str, Any]:
    """获取外观配置"""
    config = get_config()
    return config.get("appearance", {"theme": "dark", "font_size": 12, "language": "zh"})


def save_appearance(theme: str = "", font_size: int = 0, language: str = "") -> bool:
    """保存外观配置"""
    try:
        from llm_provider import load_config, save_config as _save
        config = load_config()
        app = config.setdefault("appearance", {})
        if theme:
            app["theme"] = theme
        if font_size:
            app["font_size"] = font_size
        if language:
            app["language"] = language
        _save(config)
        return True
    except Exception as e:
        logger.warning(f"save_appearance: failed: {e}")
        return False


# --- Shortcuts ---

def get_shortcuts() -> Dict[str, Any]:
    """获取快捷键配置"""
    try:
        if os.path.exists(SHORTCUT_CONFIG_FILE):
            with open(SHORTCUT_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        from core.shortcut_manager import DEFAULT_SHORTCUTS
        return {"shortcuts": {k: v.to_dict() for k, v in DEFAULT_SHORTCUTS.items()}}
    except Exception as e:
        logger.warning(f"get_shortcuts: failed: {e}")
        return {"shortcuts": {}}


def save_shortcuts(shortcuts: Dict[str, Any]) -> bool:
    """保存快捷键配置"""
    try:
        os.makedirs(SHORTCUT_CONFIG_DIR, exist_ok=True)
        with open(SHORTCUT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"shortcuts": shortcuts}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.warning(f"save_shortcuts: failed: {e}")
        return False


# --- Export / Import / Reset ---

def do_export_config() -> Dict[str, Any]:
    """导出配置到临时文件"""
    try:
        if not os.path.exists(CONFIG_FILE):
            return {"success": False, "message": "config.json 不存在"}
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"opencopilot_config_{ts}.json"
        dst = os.path.join(tempfile.gettempdir(), name)
        shutil.copy2(CONFIG_FILE, dst)
        return {"success": True, "file_path": dst, "filename": name}
    except Exception as e:
        logger.error(f"do_export_config: failed: {e}")
        return {"success": False, "message": str(e)}


def do_import_config(file_path: str) -> Dict[str, Any]:
    """从文件导入配置"""
    try:
        path = os.path.expanduser(file_path)
        if not os.path.exists(path):
            return {"success": False, "message": f"文件不存在: {path}"}
        with open(path, "r", encoding="utf-8") as f:
            imported = json.load(f)
        if not isinstance(imported, dict):
            return {"success": False, "message": "配置文件格式错误"}
        from llm_provider import save_config as _save
        _save(imported)
        return {"success": True, "imported_keys": list(imported.keys())}
    except json.JSONDecodeError:
        return {"success": False, "message": "JSON 解析失败"}
    except Exception as e:
        logger.error(f"do_import_config: failed: {e}")
        return {"success": False, "message": str(e)}


def do_reset_config(section: str = "") -> Dict[str, Any]:
    """重置配置（指定 section 或全部）"""
    try:
        from config_manager import (
            DEFAULT_AGENT_CONFIG, DEFAULT_LLM_CONFIG,
            DEFAULT_CONCURRENCY_CONFIG, DEFAULT_WEB_SEARCH_CONFIG,
        )
        from llm_provider import load_config, save_config as _save
        config = load_config()
        defaults_map = {
            "agent": DEFAULT_AGENT_CONFIG,
            "llm": DEFAULT_LLM_CONFIG,
            "concurrency": DEFAULT_CONCURRENCY_CONFIG,
            "web_search": DEFAULT_WEB_SEARCH_CONFIG,
            "appearance": {"theme": "dark", "font_size": 12, "language": "zh"},
        }
        if section:
            if section in defaults_map:
                config[section] = defaults_map[section].copy()
            elif section in config:
                del config[section]
            _save(config)
            return {"success": True, "reset_section": section}
        else:
            for s, d in defaults_map.items():
                config[s] = d.copy()
            _save(config)
            return {"success": True, "reset_sections": list(defaults_map.keys())}
    except Exception as e:
        logger.error(f"do_reset_config: failed: {e}")
        return {"success": False, "message": str(e)}


# =============================================================================
# 4. Workspace 数据
# =============================================================================

def get_recent_files(limit: int = 20) -> List[Dict]:
    """获取最近文件列表"""
    try:
        if os.path.exists(RECENT_FILES_PATH):
            with open(RECENT_FILES_PATH, "r", encoding="utf-8") as f:
                files = json.load(f)
            if isinstance(files, list):
                files.sort(key=lambda x: x.get("modified", ""), reverse=True)
                return files[:limit]
    except Exception as e:
        logger.warning(f"get_recent_files: failed: {e}")
    return []


def add_recent_file(file_path: str, source: str = "local"):
    """添加一条最近文件记录"""
    try:
        path = os.path.expanduser(file_path)
        if not os.path.exists(path):
            return
        stat = os.stat(path)
        entry = {
            "name": os.path.basename(path),
            "path": path,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "source": source,
        }
        files = []
        if os.path.exists(RECENT_FILES_PATH):
            with open(RECENT_FILES_PATH, "r", encoding="utf-8") as f:
                files = json.load(f)
            if not isinstance(files, list):
                files = []
        files = [f for f in files if f.get("path") != entry["path"]]
        files.insert(0, entry)
        files = files[:MAX_RECENT_FILES]
        os.makedirs(os.path.dirname(RECENT_FILES_PATH), exist_ok=True)
        with open(RECENT_FILES_PATH, "w", encoding="utf-8") as f:
            json.dump(files, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"add_recent_file: failed: {e}")


def get_memory_stats() -> Dict[str, Any]:
    """获取知识图谱 / 翻译记忆 / 术语库统计"""
    stats = {
        "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
        "translation_memory": {"entries": 0, "status": "unavailable"},
        "glossary": {"terms": 0, "status": "unavailable"},
    }
    # 知识图谱
    try:
        kg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               "knowledge_graph", "opencopilot_knowledge_graph.json")
        if os.path.exists(kg_path):
            with open(kg_path, "r", encoding="utf-8") as f:
                kg = json.load(f)
            stats["knowledge_graph"] = {
                "entities": len(kg.get("entities", [])),
                "relations": len(kg.get("relations", [])),
                "status": "ok",
            }
    except Exception as e:
        logger.debug(f"get_memory_stats: KG unavailable: {e}")
    # 翻译记忆 + 术语库
    try:
        from opencopilot.capabilities.memory.core import MemoryManager
        mm = MemoryManager()
        stats["translation_memory"] = {"entries": mm.count_memories(memory_type="translation"), "status": "ok"}
        stats["glossary"] = {"terms": mm.count_memories(memory_type="glossary"), "status": "ok"}
    except Exception as e:
        logger.debug(f"get_memory_stats: MemoryManager unavailable: {e}")
    return stats


def get_task_history(session_id: str = "", limit: int = 20) -> List[Dict]:
    """获取任务历史"""
    try:
        from smart_copilot_api import tasks_storage
        tasks = list(tasks_storage.values())
        if session_id:
            tasks = [t for t in tasks if t.get("session_id") == session_id]
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return tasks[:limit]
    except Exception as e:
        logger.debug(f"get_task_history: failed: {e}")
        return []
