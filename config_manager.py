"""
配置管理器（ConfigManager）

集中管理 config.json 中所有可配置参数，提供：
- 单例模式，避免重复读取文件
- 分层查询接口：get_agent() / get_llm() / get_concurrency() / get_web_search()
- 参数校验与默认值兜底
- 热重载支持

使用方式:
    from config_manager import ConfigManager
    cfg = ConfigManager.get_instance()
    agent_cfg = cfg.get_agent()       # -> {"max_turns": 10, "max_plan_steps": 5, ...}
    llm_cfg = cfg.get_llm()           # -> {"temperature": 0.7, "max_completion_tokens": 4096, ...}
    conc_cfg = cfg.get_concurrency()  # -> {"chat": 10, "coding": 3, ...}
"""

import os
import json
import threading
from typing import Any, Dict, Optional
from copy import deepcopy

CONFIG_FILE = "config.json"

# 默认值定义（当 config.json 缺失或不完整时使用）
DEFAULT_AGENT_CONFIG = {
    "max_turns": 10,
    "max_plan_steps": 5,
    "complexity_text_threshold": 200,
    "react_retry_count": 1,
}

DEFAULT_LLM_CONFIG = {
    "temperature": 0.7,
    "max_completion_tokens": 4096,
    "thinking_enabled": False,
    "failover_max_failures": 3,
    "repetition_penalty": 1.05,
}

DEFAULT_CONCURRENCY_CONFIG = {
    "chat": 10,
    "default": 10,
    "coding": 3,
    "code_execution": 2,
    "ppt": 5,
    "evaluation": 5,
    "translate": 8,
    "planning": 3,
    "skill": 3,
    "knowledge_query": 5,
    "search": 5,
}

DEFAULT_WEB_SEARCH_CONFIG = {
    "enabled": True,
    "force_search": False,
    "max_keyword": 3,
    "limit": 3,
}

# action_type → persona 文件名映射（不含 .md）
# 当 action_type 与 persona 文件名不同时在此配置
DEFAULT_PERSONA_MAPPING = {
    "ppt": "ppt",
    "coding": "code",
    "code_review": "code",
    "translate": "translate",
    "translation": "translate",
    "chat": "chat",
    "polish": "polish",
    "revision": "revision",
    "default": "default",
}

# 参数校验范围
VALID_RANGES = {
    "agent.max_turns": (3, 30),
    "agent.max_plan_steps": (2, 15),
    "agent.complexity_text_threshold": (50, 2000),
    "agent.react_retry_count": (0, 5),
    "llm.temperature": (0.0, 2.0),
    "llm.max_completion_tokens": (256, 65536),
    "llm.failover_max_failures": (1, 10),
}


class ConfigManager:
    """配置管理器单例"""

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._reload()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例（测试用）"""
        with cls._lock:
            cls._instance = None

    def _reload(self):
        """从 config.json 重新加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}
        else:
            self._config = {}

    def reload(self):
        """热重载配置（外部调用，用于运行时更新）"""
        self._reload()

    def _validate_and_clamp(self, key: str, value: Any, default: Any) -> Any:
        """校验参数并 clamp 到有效范围"""
        if key in VALID_RANGES:
            min_val, max_val = VALID_RANGES[key]
            if isinstance(value, (int, float)):
                if value < min_val:
                    print(f"[ConfigManager] ⚠️ {key}={value} 超出下限，clamp 到 {min_val}")
                    return min_val
                if value > max_val:
                    print(f"[ConfigManager] ⚠️ {key}={value} 超出上限，clamp 到 {max_val}")
                    return max_val
        return value

    def _merge_with_defaults(self, section: str, defaults: dict, prefix: str) -> dict:
        """合并用户配置和默认值，并进行校验"""
        user_section = self._config.get(section, {})
        result = deepcopy(defaults)
        if isinstance(user_section, dict):
            for k, v in user_section.items():
                if k in result:
                    validated = self._validate_and_clamp(
                        f"{prefix}.{k}", v, defaults.get(k)
                    )
                    result[k] = validated
        return result

    def get_raw(self) -> Dict[str, Any]:
        """获取原始配置 dict（只读拷贝）"""
        return deepcopy(self._config)

    def get(self, key: str, default: Any = None) -> Any:
        """通用 get 方法"""
        return self._config.get(key, default)

    # ---- 分层便捷方法 ----

    def get_agent(self) -> Dict[str, Any]:
        """获取 Agent Loop 引擎配置
        Returns:
            {
                "max_turns": 10,                    # Agent 最大推理轮次
                "max_plan_steps": 5,                # Plan-and-Solve 每任务最多生成几步
                "complexity_text_threshold": 200,   # 触发 MEDIUM 复杂度的文本长度阈值
                "react_retry_count": 1,             # 每步失败后 React 纠错次数
            }
        """
        return self._merge_with_defaults("agent", DEFAULT_AGENT_CONFIG, "agent")

    def get_llm(self) -> Dict[str, Any]:
        """获取 LLM Provider 配置
        Returns:
            {
                "temperature": 0.7,                 # 推理温度
                "max_completion_tokens": 4096,      # 最大输出 Token
                "thinking_enabled": False,          # 深度思考开关
                "failover_max_failures": 3,         # Provider 故障转移阈值
            }
        """
        return self._merge_with_defaults("llm", DEFAULT_LLM_CONFIG, "llm")

    def get_concurrency(self) -> Dict[str, int]:
        """获取并发控制配置
        Returns:
            {
                "chat": 10, ...                     # 各 action_type 最大并发数
            }
        """
        return self._merge_with_defaults("concurrency", DEFAULT_CONCURRENCY_CONFIG, "concurrency")

    def get_web_search(self) -> Dict[str, Any]:
        """获取联网搜索配置"""
        return self._merge_with_defaults("web_search", DEFAULT_WEB_SEARCH_CONFIG, "web_search")

    def get_persona_mapping(self) -> Dict[str, str]:
        """获取 action_type → persona 文件名映射
        
        Returns:
            {"ppt": "ppt", "coding": "code", ...}
            key = action_type, value = personas/ 下的文件名（不含 .md）
        """
        user_mapping = self._config.get("persona_mapping", {})
        result = dict(DEFAULT_PERSONA_MAPPING)
        if isinstance(user_mapping, dict):
            result.update(user_mapping)
        return result

    def save(self) -> bool:
        """保存当前配置到 config.json"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] 保存配置失败: {e}")
            return False

    def update_section(self, section: str, updates: dict) -> bool:
        """更新指定 section 的配置并保存"""
        if section not in self._config:
            self._config[section] = {}
        self._config[section].update(updates)
        return self.save()

    def get_context_budget(self) -> Dict[str, Any]:
        """获取上下文预算配置（供 ContextWindowManager 使用）"""
        defaults = {
            "max_input_chars": 120000,
            "reserve_output_chars": 30000,
            "recent_turns": 12,
            "max_history_msg_chars": 8000,
        }
        return self._merge_with_defaults("context_budget", defaults, "context_budget")

    def get_model_limits(self) -> Dict[str, int]:
        """获取模型上下文限制"""
        return self._config.get("model_context_limits", {
            "minimax-m2.7": 200000,
            "MiniMax-M3": 200000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
        })
