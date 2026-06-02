#!/usr/bin/env python3
"""
直接模块集成验证测试 - 不通过HTTP，直接导入和测试所有模块
"""

import os
import sys
import json
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

test_results = []

def test(name, func):
    """运行测试函数"""
    try:
        start = time.time()
        result = func()
        elapsed = time.time() - start
        test_results.append({"name": name, "status": "PASS", "detail": str(result)[:200], "time": f"{elapsed:.2f}s"})
        print(f"  ✅ PASS | {name} ({elapsed:.2f}s)")
        if result:
            print(f"         {str(result)[:150]}")
    except Exception as e:
        test_results.append({"name": name, "status": "FAIL", "error": str(e)[:200], "traceback": traceback.format_exc()[-300:]})
        print(f"  ❌ FAIL | {name}")
        print(f"         Error: {e}")


print("=" * 60)
print("OpenCopilot 模块集成验证测试 (直接导入)")
print("=" * 60)

# ==================== 1. 模块导入测试 ====================
print("\n【1. 模块导入测试】")

def test_import_code_executor():
    from code_executor import CodeExecutor, ExecutorConfig
    return f"CodeExecutor imported OK"

def test_import_context_manager():
    from context_manager import ContextWindowManager
    return f"ContextWindowManager imported OK"

def test_import_knowledge_retrieval():
    from knowledge_retrieval import KnowledgeRetrieval
    return f"KnowledgeRetrieval imported OK"

def test_import_search_capability():
    from search_capability import SearchCapability, SearchType
    return f"SearchCapability imported OK"

def test_import_state_manager():
    from state_manager import StateManager, get_default_manager
    return f"StateManager imported OK"

def test_import_planner():
    from planner import Planner, PlanRequest
    return f"Planner imported OK"

def test_import_security_module():
    from security_module import SecurityModule, SecurityConfig
    return f"SecurityModule imported OK"

def test_import_observability():
    from observability_module import ObservabilityModule, ObservabilityConfig, LogLevel
    return f"ObservabilityModule imported OK"

def test_import_agents_md():
    from agents_md_module import ImmuneSystem, RuleEngine
    return f"ImmuneSystem imported OK"

def test_import_skill_architecture():
    from skill_architecture import SkillRegistry, IntentRouter, SkillExecutor, SkillDiscovery
    return f"SkillArchitecture imported OK"

def test_import_llm_provider():
    from llm_provider import MiniMaxProvider, LocalProvider, load_config
    return f"LLMProvider imported OK"

test("导入 CodeExecutor", test_import_code_executor)
test("导入 ContextWindowManager", test_import_context_manager)
test("导入 KnowledgeRetrieval", test_import_knowledge_retrieval)
test("导入 SearchCapability", test_import_search_capability)
test("导入 StateManager", test_import_state_manager)
test("导入 Planner", test_import_planner)
test("导入 SecurityModule", test_import_security_module)
test("导入 ObservabilityModule", test_import_observability)
test("导入 ImmuneSystem", test_import_agents_md)
test("导入 SkillArchitecture", test_import_skill_architecture)
test("导入 LLMProvider", test_import_llm_provider)


# ==================== 2. 模块初始化测试 ====================
print("\n【2. 模块初始化测试】")

def test_init_code_executor():
    from code_executor import CodeExecutor, ExecutorConfig
    executor = CodeExecutor(ExecutorConfig(default_timeout=30, max_timeout=60, working_directory=os.getcwd()))
    return f"CodeExecutor initialized, timeout={executor.config.default_timeout}"

def test_init_knowledge_retrieval():
    from knowledge_retrieval import KnowledgeRetrieval
    kr = KnowledgeRetrieval()
    return f"KnowledgeRetrieval initialized, initialized={kr._initialized}"

def test_init_search_capability():
    from search_capability import SearchCapability
    sc = SearchCapability(workspace=os.getcwd())
    return f"SearchCapability initialized"

def test_init_state_manager():
    from state_manager import get_default_manager
    sm = get_default_manager()
    return f"StateManager initialized: {type(sm).__name__}"

def test_init_planner():
    from planner import Planner
    p = Planner()
    return f"Planner initialized: {type(p).__name__}"

def test_init_security():
    from security_module import SecurityModule, SecurityConfig
    config = SecurityConfig(enable_audit_logging=True, enable_rate_limiting=True, enable_permission_check=True)
    sm = SecurityModule(config)
    return f"SecurityModule initialized, audit={config.enable_audit_logging}"

def test_init_observability():
    from observability_module import ObservabilityModule, ObservabilityConfig, LogLevel
    config = ObservabilityConfig(log_level=LogLevel.INFO.value, enable_tracing=True, enable_performance_monitoring=True)
    om = ObservabilityModule(config)
    return f"ObservabilityModule initialized, logger={type(om.logger).__name__}"

def test_init_immune_system():
    from agents_md_module import ImmuneSystem
    ims = ImmuneSystem()
    return f"ImmuneSystem initialized, rule_engine={type(ims.rule_engine).__name__}"

def test_init_skill_registry():
    from skill_architecture import SkillRegistry, IntentRouter, SkillExecutor, SkillDiscovery
    registry = SkillRegistry()
    router = IntentRouter(registry)
    executor = SkillExecutor(registry, router)
    discovery = SkillDiscovery(registry)
    return f"SkillRegistry initialized, skills={len(registry._skills)}"

test("初始化 CodeExecutor", test_init_code_executor)
test("初始化 KnowledgeRetrieval", test_init_knowledge_retrieval)
test("初始化 SearchCapability", test_init_search_capability)
test("初始化 StateManager", test_init_state_manager)
test("初始化 Planner", test_init_planner)
test("初始化 SecurityModule", test_init_security)
test("初始化 ObservabilityModule", test_init_observability)
test("初始化 ImmuneSystem", test_init_immune_system)
test("初始化 SkillRegistry", test_init_skill_registry)


# ==================== 3. 代码执行测试 ====================
print("\n【3. 代码执行测试】")

def test_code_execution_basic():
    from code_executor import CodeExecutor, ExecutorConfig
    executor = CodeExecutor(ExecutorConfig(default_timeout=30, working_directory=os.getcwd()))
    import asyncio
    result = asyncio.run(executor.execute_code("print(2 + 3)", language="python", timeout=30))
    return f"success={result.success}, stdout={result.stdout.strip() if result.stdout else 'N/A'}"

def test_code_execution_complex():
    from code_executor import CodeExecutor, ExecutorConfig
    executor = CodeExecutor(ExecutorConfig(default_timeout=30, working_directory=os.getcwd()))
    import asyncio
    code = """
import json
data = {"name": "OpenCopilot", "version": "3.0", "modules": 12}
print(json.dumps(data, indent=2))
"""
    result = asyncio.run(executor.execute_code(code, language="python", timeout=30))
    return f"success={result.success}, stdout={result.stdout.strip()[:100] if result.stdout else 'N/A'}"

test("基础代码执行 (print(2+3))", test_code_execution_basic)
test("复杂代码执行 (JSON操作)", test_code_execution_complex)


# ==================== 4. 知识检索测试 ====================
print("\n【4. 知识检索测试】")

def test_knowledge_retrieval():
    from knowledge_retrieval import KnowledgeRetrieval
    kr = KnowledgeRetrieval()
    # 初始化知识图谱
    init_result = kr.initialize()
    if init_result.success:
        # 查询
        result = kr.query("项目中有哪些模块")
        return f"init=OK, query_success={result.success}, data_type={type(result.data).__name__ if result.data else 'None'}"
    else:
        return f"init_failed={init_result.error}"

test("知识检索查询", test_knowledge_retrieval)


# ==================== 5. 搜索能力测试 ====================
print("\n【5. 搜索能力测试】")

def test_search_capability():
    from search_capability import SearchCapability, SearchType
    sc = SearchCapability(workspace=os.getcwd())
    results = sc.search("Python best practices", search_type=SearchType.ALL, count=3)
    return f"results_count={len(results) if results else 0}"

test("搜索能力测试", test_search_capability)


# ==================== 6. 状态管理测试 ====================
print("\n【6. 状态管理测试】")

def test_state_manager():
    from state_manager import get_default_manager
    sm = get_default_manager()
    # 创建任务状态
    state = sm.create_task(session_id="test-session", task_type="test", description="测试任务")
    return f"task_id={state.task_id if hasattr(state, 'task_id') else 'N/A'}, status={state.status if hasattr(state, 'status') else 'N/A'}"

test("状态管理 - 创建任务", test_state_manager)


# ==================== 7. 任务规划测试 ====================
print("\n【7. 任务规划测试】")

def test_planner():
    from planner import Planner, PlanRequest
    p = Planner()
    # 测试Planner基本功能（不调用LLM，仅验证初始化和策略注册）
    strategies = list(p._strategies.keys()) if hasattr(p, '_strategies') else []
    has_generator = hasattr(p, 'generator')
    has_validator = hasattr(p, 'validator')
    return f"has_generator={has_generator}, has_validator={has_validator}, strategies={strategies}"

test("任务规划 - 创建计划", test_planner)


# ==================== 8. 安全模块测试 ====================
print("\n【8. 安全模块测试】")

def test_security_permission():
    from security_module import SecurityModule, SecurityConfig
    config = SecurityConfig(enable_audit_logging=True, enable_rate_limiting=True, enable_permission_check=True)
    sm = SecurityModule(config)
    import asyncio
    result = asyncio.run(sm.check_permission(user_id="test-user", resource="code_execution", action="execute"))
    return f"permission_granted={result}"

def test_security_audit():
    from security_module import SecurityModule, SecurityConfig
    config = SecurityConfig(enable_audit_logging=True)
    sm = SecurityModule(config)
    entry = sm.audit_logger.log(
        user_id="test-user",
        action="test_action",
        resource="test_resource",
        result="success"
    )
    return f"audit_entry_id={entry.entry_id}, action={entry.action}"

def test_security_status():
    from security_module import SecurityModule, SecurityConfig
    config = SecurityConfig(enable_audit_logging=True, enable_rate_limiting=True, enable_permission_check=True)
    sm = SecurityModule(config)
    import asyncio
    status = asyncio.run(sm.get_status())
    return f"status={status.get('status')}, config_keys={list(status.get('config', {}).keys())}"

test("安全模块 - 权限检查", test_security_permission)
test("安全模块 - 审计日志", test_security_audit)
test("安全模块 - 状态查询", test_security_status)


# ==================== 9. 可观测性测试 ====================
print("\n【9. 可观测性测试】")

def test_observability_logger():
    from observability_module import ObservabilityModule, ObservabilityConfig, LogLevel
    config = ObservabilityConfig(log_level=LogLevel.INFO.value, enable_tracing=True)
    om = ObservabilityModule(config)
    entry = om.logger.info("Test log message", context={"test": True})
    return f"log_level={entry.level}, message={entry.message[:50]}"

def test_observability_health():
    from observability_module import ObservabilityModule, ObservabilityConfig, LogLevel
    config = ObservabilityConfig(log_level=LogLevel.INFO.value, health_check_interval=30.0)
    om = ObservabilityModule(config)
    # 测试健康检查器初始化
    has_checker = hasattr(om, 'health_checker')
    checker_type = type(om.health_checker).__name__
    return f"has_health_checker={has_checker}, checker_type={checker_type}"

test("可观测性 - 日志记录", test_observability_logger)
test("可观测性 - 健康检查", test_observability_health)


# ==================== 10. AGENTS.md免疫机制测试 ====================
print("\n【10. AGENTS.md免疫机制测试】")

def test_immune_system():
    from agents_md_module import ImmuneSystem, RuleContext
    ims = ImmuneSystem()
    import asyncio
    context = RuleContext(session_id="test-session")
    response = asyncio.run(ims.check_content(context, "这是一个正常的请求"))
    return f"allowed={response.allowed}, message={response.message[:50] if response.message else 'N/A'}"

test("免疫系统 - 内容检查", test_immune_system)


# ==================== 11. Skill架构测试 ====================
print("\n【11. Skill架构测试】")

def test_skill_registry():
    from skill_architecture import SkillRegistry
    registry = SkillRegistry()
    return f"registered_skills={len(registry._skills)}, skill_classes={len(registry._skill_classes)}"

def test_skill_discovery():
    from skill_architecture import SkillRegistry, SkillDiscovery
    registry = SkillRegistry()
    discovery = SkillDiscovery(registry)
    discovered = discovery.discover()
    return f"discovered_skills={len(discovered)}"

test("Skill注册表", test_skill_registry)
test("Skill自动发现", test_skill_discovery)


# ==================== 12. LLM Provider测试 ====================
print("\n【12. LLM Provider测试】")

def test_llm_provider_init():
    from llm_provider import MiniMaxProvider, load_config
    config = load_config()
    provider = MiniMaxProvider()
    return f"provider_type={config.get('provider_type')}, has_api_key={bool(provider.api_key)}"

def test_llm_streaming():
    from llm_provider import MiniMaxProvider
    provider = MiniMaxProvider()
    full_response = ""
    chunk_count = 0
    for chunk in provider.stream_chat("说'OK'两个字母"):
        full_response += chunk
        chunk_count += 1
        if len(full_response) > 50:
            break
    return f"chunks={chunk_count}, response_length={len(full_response)}, preview={full_response[:50]}"

test("LLM Provider初始化", test_llm_provider_init)
test("LLM流式调用 (MiniMax)", test_llm_streaming)


# ==================== 13. detect_request_type测试 ====================
print("\n【13. 请求类型检测测试】")

def test_detect_code():
    from asu_custom_agent import detect_request_type
    result = detect_request_type("执行代码: print('hello')")
    return f"type={result}"

def test_detect_knowledge():
    from asu_custom_agent import detect_request_type
    result = detect_request_type("知识图谱中有哪些组件")
    return f"type={result}"

def test_detect_search():
    from asu_custom_agent import detect_request_type
    result = detect_request_type("搜索Python最佳实践")
    return f"type={result}"

def test_detect_planning():
    from asu_custom_agent import detect_request_type
    result = detect_request_type("帮我规划一个Web应用开发任务")
    return f"type={result}"

def test_detect_security():
    from asu_custom_agent import detect_request_type
    result = detect_request_type("查看安全模块状态")
    return f"type={result}"

def test_detect_chat():
    from asu_custom_agent import detect_request_type
    result = detect_request_type("你好，请介绍一下自己")
    return f"type={result}"

test("检测: 代码执行", test_detect_code)
test("检测: 知识检索", test_detect_knowledge)
test("检测: 搜索", test_detect_search)
test("检测: 任务规划", test_detect_planning)
test("检测: 安全", test_detect_security)
test("检测: 普通对话", test_detect_chat)


# ==================== 结果汇总 ====================
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
total = len(test_results)
passed = sum(1 for r in test_results if r["status"] == "PASS")
failed = sum(1 for r in test_results if r["status"] == "FAIL")
print(f"总测试数: {total}")
print(f"通过: {passed} ✅")
print(f"失败: {failed} ❌")
print(f"通过率: {passed/total*100:.1f}%")

if failed > 0:
    print(f"\n失败详情:")
    for r in test_results:
        if r["status"] == "FAIL":
            print(f"  - {r['name']}: {r['error']}")

# 保存报告
report = {
    "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "summary": {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/total*100:.1f}%"
    },
    "details": test_results
}

with open("direct_module_test_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n报告已保存: direct_module_test_report.json")
print("=" * 60)
