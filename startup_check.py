#!/usr/bin/env python3
"""
启动完整性检查 — 模拟外置终端环境，一次性验证所有入口
"""
import sys, traceback, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("═══ OpenCopilot 启动完整性检查 ═══\n")
errors = []
oks = 0

def check(name, code):
    global oks
    try:
        exec(code, {})
        oks += 1
        print(f"  ✅ {name}")
    except Exception as e:
        errors.append((name, str(e)))
        print(f"  ❌ {name}: {e}")

# ====================
# 第1组：核心导入
# ====================
print("--- 核心导入 ---")
check("config_manager", "from config_manager import ConfigManager")
check("llm_provider", "from llm_provider import load_config, ProviderFactory")
check("smart_copilot_api", "from smart_copilot_api import app")
check("ppt_generator", "import ppt_generator")

# ====================
# 第2组：Agent/Pipeline
# ====================
print("--- Agent Pipeline ---")
check("agent.pipeline", "from opencopilot.agent.pipeline import PipelineContext, MiddlewarePipeline")
check("agent.middlewares", "from opencopilot.agent import SessionSetupMiddleware, LLMAgentMiddleware")
check("agent.caller", "from opencopilot.agent.caller import call_agent_pipeline_sync")
check("agent.core", "from opencopilot.agent.core import ContextWindowManager")

# ====================
# 第3组：能力模块
# ====================
print("--- 能力模块 ---")
check("coding", "from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig, CodeExecutionRequest")
check("ppt", "from opencopilot.capabilities.ppt import CoCreationDialog")
check("skill.registry", "from opencopilot.capabilities.skill import SkillRegistry, SkillExecutor, IntentRouter")
check("skill.models", "from opencopilot.capabilities.skill.models import SkillMetadata")

# ====================
# 第4组：Skill 实例化（验证 metadata 完整性）
# ====================
print("--- Skill 实例化 ---")
for cls_name in ['KnowledgeSkill','CodingSkill','PPTSkill','EvaluationSkill','FileSkill','FormatSkill','PersonaSkill']:
    check(f"skill.{cls_name}", f"""
from opencopilot.capabilities.skill import {cls_name}
s = {cls_name}()
m = s.metadata
# 验证所有字段可访问
_ = (m.name, m.version, m.description, m.author, m.category, m.display_name, m.shortcut, m.tags, m.intents)
""")

# ====================
# 第5组：安全模块
# ====================
print("--- 安全模块 ---")
check("immune.system", "from opencopilot.safety.immune.immune_system import ImmuneSystem")
check("immune.models", "from opencopilot.safety.immune.models import RuleContext, ImmuneResponse")
check("immune.rule_engine", "from opencopilot.safety.immune.rule_engine import RuleEngine")
check("security.core", "from opencopilot.safety.security.core import SecurityModule")
check("security.api", "from opencopilot.safety.security.api import create_security_router")

# ====================
# 第6组：GUI 导入
# ====================
print("--- GUI 模块 ---")
check("gui.main", "from gui.main import CopilotManager")
check("gui.window", "from gui.window import AICardWindow")
check("gui.workspace", "from gui.workspace import AgentWorkspace")
check("gui.shared", "from gui.shared import check_accessibility_permission")
check("gui.workers.ai", "from gui.workers.ai import AIWorker")
check("gui.workers.chat", "from gui.workers.chat import ChatWorker")
check("gui.workers.broker", "from gui.workers.broker import BrokerEventsWorker")
check("gui.workers.mouse", "from gui.workers.mouse import MouseListenerWorker")
check("gui.workers.health", "from gui.workers.health import AgentHealthWorker")

# ====================
# 第7组：Widgets（需要 PyQt）  
# ====================
print("--- Widgets ---")
check("skill_context_menu", "import widgets.skill_context_menu")
check("skill_panel", "from widgets.skill_panel import SkillPanel")

# ====================
# 第8组：翻译/评估
# ====================
print("--- 翻译/评估 ---")
check("translation_dialog", "from dialogs.translation_dialog import TranslationDialog")
check("evaluation_tools", "from opencopilot.capabilities.tools.evaluation_tools import TranslateEvaluator")

# ====================
# 结果
# ====================
print(f"\n{'='*50}")
print(f"通过: {oks} | 失败: {len(errors)}")
if errors:
    print(f"\n失败详情:")
    for name, err in errors:
        print(f"  {name}: {err}")
    print(f"\n❌ 需修复 {len(errors)} 个问题")
    sys.exit(1)
else:
    print(f"\n✅ 全部通过！可以安全启动")
    sys.exit(0)
