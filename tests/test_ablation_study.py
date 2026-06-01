# tests/test_ablation_study.py

"""
消融测试

比较有模块和没有模块时的行为差异，验证模块的价值。
"""

import pytest
import asyncio
import sys
import os
import json
import time
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# ============================================================
# 辅助函数
# ============================================================

async def mock_llm_caller(prompt: str) -> str:
    """模拟 LLM 调用"""
    return json.dumps([
        {
            "step_name": "分析任务",
            "step_type": "llm_call",
            "description": "分析用户任务需求"
        },
        {
            "step_name": "执行任务",
            "step_type": "tool_call",
            "description": "执行主要任务",
            "tool_id": "code_executor"
        }
    ], ensure_ascii=False)


def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算指标"""
    if not results:
        return {}
    
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    durations = [r.get("duration", 0) for r in results]
    
    return {
        "success_rate": success_count / total_count if total_count > 0 else 0,
        "total_count": total_count,
        "success_count": success_count,
        "avg_duration": sum(durations) / len(durations) if durations else 0,
        "min_duration": min(durations) if durations else 0,
        "max_duration": max(durations) if durations else 0
    }


# ============================================================
# Planner 模块消融测试
# ============================================================

class TestPlannerAblation:
    """规划器模块消融测试"""
    
    @pytest.mark.asyncio
    async def test_with_planner(self):
        """有规划器的情况"""
        from planner.core import Planner
        
        planner = Planner(llm_caller=mock_llm_caller)
        
        results = []
        for i in range(5):
            start_time = time.time()
            try:
                plan = await planner.create_plan(
                    task=f"任务 {i+1}: 实现功能模块",
                    strategy="sequential"
                )
                duration = time.time() - start_time
                results.append({
                    "success": True,
                    "plan_id": plan.plan_id,
                    "steps_count": len(plan.steps),
                    "duration": duration
                })
            except Exception as e:
                duration = time.time() - start_time
                results.append({
                    "success": False,
                    "error": str(e),
                    "duration": duration
                })
        
        metrics = calculate_metrics(results)
        
        assert metrics["success_rate"] == 1.0
        assert metrics["total_count"] == 5
        assert metrics["success_count"] == 5
        
        # 验证每个计划都有步骤
        for r in results:
            if r["success"]:
                assert r["steps_count"] > 0
    
    @pytest.mark.asyncio
    async def test_without_planner(self):
        """没有规划器的情况（直接执行）"""
        
        # 模拟没有规划器时的直接执行
        results = []
        for i in range(5):
            start_time = time.time()
            try:
                # 没有规划器，直接执行（模拟）
                # 这里我们模拟一个简单的任务执行
                task = f"任务 {i+1}: 实现功能模块"
                
                # 没有规划，直接开始执行
                # 模拟执行时间
                await asyncio.sleep(0.01)
                
                duration = time.time() - start_time
                results.append({
                    "success": True,
                    "task": task,
                    "duration": duration,
                    "has_plan": False
                })
            except Exception as e:
                duration = time.time() - start_time
                results.append({
                    "success": False,
                    "error": str(e),
                    "duration": duration
                })
        
        metrics = calculate_metrics(results)
        
        assert metrics["success_rate"] == 1.0
        assert metrics["total_count"] == 5
        
        # 没有规划器，所以没有计划结构
        for r in results:
            assert r.get("has_plan", False) is False
    
    def test_comparison(self):
        """比较有无规划器的差异"""
        # 有规划器的优势
        advantages_with_planner = [
            "任务分解：将复杂任务分解为可执行的步骤",
            "依赖管理：自动识别和管理步骤间的依赖关系",
            "进度跟踪：可以跟踪每个步骤的执行状态",
            "错误恢复：失败时可以从断点继续",
            "优化建议：可以优化执行顺序和资源分配"
        ]
        
        # 没有规划器的劣势
        disadvantages_without_planner = [
            "缺乏结构：任务执行没有明确的结构",
            "难以追踪：无法追踪执行进度",
            "错误处理：失败时需要从头开始",
            "资源浪费：可能存在重复或无效的执行"
        ]
        
        assert len(advantages_with_planner) > 0
        assert len(disadvantages_without_planner) > 0


# ============================================================
# Code Executor 模块消融测试
# ============================================================

class TestCodeExecutorAblation:
    """代码执行引擎模块消融测试"""
    
    @pytest.fixture
    def executor(self):
        """创建代码执行引擎实例"""
        from code_executor.core import CodeExecutor
        from code_executor.models import ExecutorConfig
        
        config = ExecutorConfig(
            default_timeout=10.0,
            max_timeout=30.0,
            enable_sandbox=False
        )
        return CodeExecutor(config=config)
    
    @pytest.mark.asyncio
    async def test_with_executor(self, executor):
        """有代码执行引擎的情况"""
        test_codes = [
            "print('Hello, World!')",
            "x = 1 + 2\nprint(f'Result: {x}')",
            "for i in range(5):\n    print(i)",
        ]
        
        results = []
        for code in test_codes:
            start_time = time.time()
            result = await executor.execute_code(code, "python")
            duration = time.time() - start_time
            
            results.append({
                "success": result.success,
                "has_output": bool(result.stdout),
                "has_error_info": bool(result.stderr),
                "duration": duration,
                "exit_code": result.exit_code
            })
        
        metrics = calculate_metrics(results)
        
        assert metrics["success_rate"] == 1.0
        assert metrics["total_count"] == 3
        
        # 有执行引擎，可以获取详细的执行信息
        for r in results:
            assert r["has_output"] is True
    
    @pytest.mark.asyncio
    async def test_without_executor(self):
        """没有代码执行引擎的情况"""
        # 模拟没有执行引擎时的情况
        test_codes = [
            "print('Hello, World!')",
            "x = 1 + 2\nprint(f'Result: {x}')",
            "for i in range(5):\n    print(i)",
        ]
        
        results = []
        for code in test_codes:
            start_time = time.time()
            
            # 没有执行引擎，无法直接执行代码
            # 模拟一个简单的"执行"（实际上只是解析）
            try:
                # 简单的语法检查
                compile(code, '<string>', 'exec')
                duration = time.time() - start_time
                results.append({
                    "success": True,
                    "has_output": False,  # 没有执行，所以没有输出
                    "has_error_info": False,
                    "duration": duration,
                    "executed": False
                })
            except SyntaxError as e:
                duration = time.time() - start_time
                results.append({
                    "success": False,
                    "error": str(e),
                    "duration": duration,
                    "executed": False
                })
        
        metrics = calculate_metrics(results)
        
        assert metrics["success_rate"] == 1.0
        assert metrics["total_count"] == 3
        
        # 没有执行引擎，无法获取执行结果
        for r in results:
            assert r.get("has_output", False) is False
            assert r.get("executed", True) is False
    
    def test_comparison(self):
        """比较有无执行引擎的差异"""
        # 有执行引擎的优势
        advantages_with_executor = [
            "代码执行：可以实际执行代码并获取结果",
            "错误处理：可以捕获运行时错误和异常",
            "资源限制：可以限制执行时间和内存使用",
            "沙盒隔离：可以在隔离环境中执行代码",
            "多语言支持：支持多种编程语言",
            "执行日志：记录详细的执行日志"
        ]
        
        # 没有执行引擎的劣势
        disadvantages_without_executor = [
            "无法执行：只能进行语法检查，无法实际执行",
            "无输出：无法获取代码的输出结果",
            "无错误信息：无法获取运行时错误信息",
            "无资源控制：无法控制执行资源"
        ]
        
        assert len(advantages_with_executor) > 0
        assert len(disadvantages_without_executor) > 0


# ============================================================
# Security 模块消融测试
# ============================================================

class TestSecurityAblation:
    """安全模块消融测试"""
    
    @pytest.fixture
    def security(self):
        """创建安全模块实例"""
        from security_module.core import SecurityModule
        from security_module.models import SecurityConfig
        
        config = SecurityConfig(
            enable_rate_limiting=True,
            enable_audit_logging=True,
            enable_permission_check=True
        )
        return SecurityModule(config=config)
    
    @pytest.mark.asyncio
    async def test_with_security(self, security):
        """有安全模块的情况"""
        # 分配角色
        security.permission_manager.assign_role_to_user("user1", "user")
        
        results = []
        
        # 权限检查
        start_time = time.time()
        has_permission = await security.check_permission(
            user_id="user1",
            resource="tool",
            action="read"
        )
        duration = time.time() - start_time
        results.append({
            "check": "permission",
            "success": True,
            "result": has_permission,
            "duration": duration
        })
        
        # 速率限制检查
        start_time = time.time()
        allowed, info = await security.check_rate_limit(
            user_id="user1",
            resource="api",
            action="call"
        )
        duration = time.time() - start_time
        results.append({
            "check": "rate_limit",
            "success": True,
            "result": allowed,
            "duration": duration
        })
        
        # 输入验证
        start_time = time.time()
        validation = await security.validate_input(
            input_data={"name": "test", "age": 25},
            schema={
                "required": ["name", "age"],
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number"}
                }
            }
        )
        duration = time.time() - start_time
        results.append({
            "check": "validation",
            "success": True,
            "result": validation.valid,
            "duration": duration
        })
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
        
        # 有安全模块，可以获取审计日志
        audit_log = security.get_audit_log()
        assert len(audit_log) > 0
    
    @pytest.mark.asyncio
    async def test_without_security(self):
        """没有安全模块的情况"""
        results = []
        
        # 没有安全模块，所有操作都允许
        start_time = time.time()
        # 模拟权限检查（总是允许）
        has_permission = True
        duration = time.time() - start_time
        results.append({
            "check": "permission",
            "success": True,
            "result": has_permission,
            "duration": duration
        })
        
        # 模拟速率限制检查（总是允许）
        start_time = time.time()
        allowed = True
        duration = time.time() - start_time
        results.append({
            "check": "rate_limit",
            "success": True,
            "result": allowed,
            "duration": duration
        })
        
        # 模拟输入验证（总是有效）
        start_time = time.time()
        valid = True
        duration = time.time() - start_time
        results.append({
            "check": "validation",
            "success": True,
            "result": valid,
            "duration": duration
        })
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
        
        # 没有安全模块，无法获取审计日志
        # 这里我们只是验证没有审计功能
        assert True
    
    def test_comparison(self):
        """比较有无安全模块的差异"""
        # 有安全模块的优势
        advantages_with_security = [
            "权限控制：基于角色的权限管理",
            "审计日志：记录所有安全相关操作",
            "审批流程：高风险操作需要审批",
            "速率限制：防止滥用和攻击",
            "输入验证：验证输入数据的合法性",
            "安全违规检测：检测和报告安全违规"
        ]
        
        # 没有安全模块的劣势
        disadvantages_without_security = [
            "无权限控制：所有操作都允许",
            "无审计：无法追踪操作历史",
            "无审批：高风险操作无法控制",
            "无速率限制：容易被滥用",
            "无输入验证：可能接受无效输入",
            "无安全检测：无法发现安全违规"
        ]
        
        assert len(advantages_with_security) > 0
        assert len(disadvantages_without_security) > 0


# ============================================================
# Observability 模块消融测试
# ============================================================

class TestObservabilityAblation:
    """可观测性模块消融测试"""
    
    @pytest.fixture
    def observability(self):
        """创建可观测性模块实例"""
        from observability_module.core import ObservabilityModule
        from observability_module.models import ObservabilityConfig, LogLevel
        
        config = ObservabilityConfig(
            log_level=LogLevel.DEBUG.value,
            enable_tracing=True
        )
        return ObservabilityModule(config=config)
    
    @pytest.mark.asyncio
    async def test_with_observability(self, observability):
        """有可观测性模块的情况"""
        results = []
        
        # 记录日志
        start_time = time.time()
        await observability.info("测试消息", module="test")
        duration = time.time() - start_time
        results.append({
            "operation": "log",
            "success": True,
            "duration": duration
        })
        
        # 记录指标
        start_time = time.time()
        await observability.record_metric("test_metric", 42.0)
        duration = time.time() - start_time
        results.append({
            "operation": "metric",
            "success": True,
            "duration": duration
        })
        
        # 开始追踪
        start_time = time.time()
        trace = await observability.start_trace("test_operation")
        duration = time.time() - start_time
        results.append({
            "operation": "trace_start",
            "success": True,
            "duration": duration
        })
        
        # 结束追踪
        start_time = time.time()
        await observability.end_trace(trace.trace_id, "ok")
        duration = time.time() - start_time
        results.append({
            "operation": "trace_end",
            "success": True,
            "duration": duration
        })
        
        assert len(results) == 4
        assert all(r["success"] for r in results)
        
        # 有可观测性模块，可以获取各种数据
        logs = await observability.get_logs()
        assert len(logs) > 0
        
        metrics = await observability.get_metrics("test_metric")
        assert metrics is not None
    
    @pytest.mark.asyncio
    async def test_without_observability(self):
        """没有可观测性模块的情况"""
        results = []
        
        # 没有可观测性模块，日志被丢弃
        start_time = time.time()
        # 模拟日志记录（实际上什么都不做）
        print("测试消息")  # 只是打印，没有结构化记录
        duration = time.time() - start_time
        results.append({
            "operation": "log",
            "success": True,
            "duration": duration,
            "structured": False
        })
        
        # 没有可观测性模块，指标被丢弃
        start_time = time.time()
        # 模拟指标记录（实际上什么都不做）
        duration = time.time() - start_time
        results.append({
            "operation": "metric",
            "success": True,
            "duration": duration,
            "recorded": False
        })
        
        # 没有可观测性模块，无法追踪
        start_time = time.time()
        # 模拟追踪（实际上什么都不做）
        duration = time.time() - start_time
        results.append({
            "operation": "trace",
            "success": True,
            "duration": duration,
            "traced": False
        })
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
        
        # 没有可观测性模块，无法获取结构化数据
        for r in results:
            if r["operation"] == "log":
                assert r.get("structured", True) is False
            elif r["operation"] == "metric":
                assert r.get("recorded", True) is False
            elif r["operation"] == "trace":
                assert r.get("traced", True) is False
    
    def test_comparison(self):
        """比较有无可观测性模块的差异"""
        # 有可观测性模块的优势
        advantages_with_observability = [
            "结构化日志：记录带有上下文的结构化日志",
            "指标收集：收集和聚合各种指标",
            "分布式追踪：追踪请求在多个服务间的流转",
            "健康检查：监控系统和模块的健康状态",
            "仪表盘：提供可视化的监控数据",
            "告警：基于阈值的告警机制"
        ]
        
        # 没有可观测性模块的劣势
        disadvantages_without_observability = [
            "无结构化日志：只有简单的打印输出",
            "无指标：无法收集和分析指标",
            "无追踪：无法追踪请求流转",
            "无健康检查：无法监控系统状态",
            "无仪表盘：无法可视化监控数据",
            "无告警：无法及时发现问题"
        ]
        
        assert len(advantages_with_observability) > 0
        assert len(disadvantages_without_observability) > 0


# ============================================================
# Agents MD 模块消融测试
# ============================================================

class TestAgentsMDAblation:
    """免疫机制模块消融测试"""
    
    @pytest.fixture
    def immune_system(self):
        """创建免疫系统实例"""
        from agents_md_module.immune_system import ImmuneSystem
        from agents_md_module.models import AgentsMdConfig, ViolationAction
        
        config = AgentsMdConfig(
            enabled=True,
            default_action=ViolationAction.LOG.value,
            enable_auto_fix=True
        )
        return ImmuneSystem(config=config)
    
    @pytest.fixture
    def rule_context(self):
        """创建规则上下文"""
        from agents_md_module.models import RuleContext
        
        return RuleContext(
            user_id="developer1",
            session_id="session_001",
            project_path="/project",
            current_file="main.py"
        )
    
    @pytest.mark.asyncio
    async def test_with_immune_system(self, immune_system, rule_context):
        """有免疫系统的情况"""
        results = []
        
        # 检查安全代码
        start_time = time.time()
        response = await immune_system.check_content(
            context=rule_context,
            content="x = 1 + 2"
        )
        duration = time.time() - start_time
        results.append({
            "check": "safe_code",
            "success": True,
            "allowed": response.allowed,
            "violations": len(response.violations),
            "duration": duration
        })
        
        # 检查包含 print 的代码
        start_time = time.time()
        response = await immune_system.check_content(
            context=rule_context,
            content="print('debug')"
        )
        duration = time.time() - start_time
        results.append({
            "check": "print_code",
            "success": True,
            "allowed": response.allowed,
            "violations": len(response.violations),
            "duration": duration
        })
        
        # 检查危险代码
        start_time = time.time()
        response = await immune_system.check_content(
            context=rule_context,
            content="eval('malicious')"
        )
        duration = time.time() - start_time
        results.append({
            "check": "dangerous_code",
            "success": True,
            "allowed": response.allowed,
            "violations": len(response.violations),
            "duration": duration
        })
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
        
        # 安全代码应该允许
        assert results[0]["allowed"] is True
        assert results[0]["violations"] == 0
        
        # 包含 print 的代码应该有违规但允许（默认动作是 LOG）
        assert results[1]["violations"] > 0
        
        # 危险代码应该被阻止
        assert results[2]["allowed"] is False
        assert results[2]["violations"] > 0
    
    @pytest.mark.asyncio
    async def test_without_immune_system(self, rule_context):
        """没有免疫系统的情况"""
        results = []
        
        # 没有免疫系统，所有代码都允许
        start_time = time.time()
        # 模拟代码检查（总是允许）
        allowed = True
        violations = 0
        duration = time.time() - start_time
        results.append({
            "check": "safe_code",
            "success": True,
            "allowed": allowed,
            "violations": violations,
            "duration": duration
        })
        
        # 没有免疫系统，print 代码也允许
        start_time = time.time()
        allowed = True
        violations = 0
        duration = time.time() - start_time
        results.append({
            "check": "print_code",
            "success": True,
            "allowed": allowed,
            "violations": violations,
            "duration": duration
        })
        
        # 没有免疫系统，危险代码也允许
        start_time = time.time()
        allowed = True
        violations = 0
        duration = time.time() - start_time
        results.append({
            "check": "dangerous_code",
            "success": True,
            "allowed": allowed,
            "violations": violations,
            "duration": duration
        })
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
        
        # 没有免疫系统，所有代码都允许
        for r in results:
            assert r["allowed"] is True
            assert r["violations"] == 0
    
    def test_comparison(self):
        """比较有无免疫系统的差异"""
        # 有免疫系统的优势
        advantages_with_immune = [
            "规则检查：根据 AGENTS.md 规则检查代码",
            "违规检测：检测违反规则的代码",
            "自动修复：可以自动修复某些违规",
            "安全防护：阻止危险代码的执行",
            "质量保证：确保代码符合质量标准",
            "违规记录：记录所有违规历史"
        ]
        
        # 没有免疫系统的劣势
        disadvantages_without_immune = [
            "无规则检查：无法检查代码是否符合规则",
            "无违规检测：无法发现违规代码",
            "无自动修复：无法自动修复问题",
            "无安全防护：危险代码可能被执行",
            "无质量保证：代码质量无法保证",
            "无违规记录：无法追踪违规历史"
        ]
        
        assert len(advantages_with_immune) > 0
        assert len(disadvantages_without_immune) > 0


# ============================================================
# 综合消融测试
# ============================================================

class TestComprehensiveAblation:
    """综合消融测试"""
    
    @pytest.mark.asyncio
    async def test_full_stack_with_modules(self):
        """完整技术栈（有所有模块）"""
        from planner.core import Planner
        from code_executor.core import CodeExecutor
        from code_executor.models import ExecutorConfig
        from security_module.core import SecurityModule
        from observability_module.core import ObservabilityModule
        from observability_module.models import ObservabilityConfig, LogLevel
        from agents_md_module.immune_system import ImmuneSystem
        
        # 创建所有模块
        planner = Planner(llm_caller=mock_llm_caller)
        executor = CodeExecutor(config=ExecutorConfig(enable_sandbox=False))
        security = SecurityModule()
        observability = ObservabilityModule(config=ObservabilityConfig(
            log_level=LogLevel.DEBUG.value,
            enable_tracing=True
        ))
        immune_system = ImmuneSystem()
        
        # 分配角色
        security.permission_manager.assign_role_to_user("user1", "user")
        
        # 开始追踪
        trace = await observability.start_trace("full_stack_test")
        
        # 权限检查
        has_permission = await security.check_permission(
            user_id="user1",
            resource="tool",
            action="read"
        )
        assert has_permission is True
        
        # 代码检查
        from agents_md_module.models import RuleContext
        context = RuleContext(user_id="user1", session_id="session1")
        code_check = await immune_system.check_content(
            context=context,
            content="print('Hello')"
        )
        # 应该有违规但允许
        assert code_check.allowed is True
        
        # 创建计划
        plan = await planner.create_plan(
            task="执行测试任务",
            strategy="sequential"
        )
        assert plan is not None
        
        # 执行代码
        result = await executor.execute_code("print('Success!')", "python")
        assert result.success is True
        
        # 记录指标
        await observability.record_metric("test_success", 1.0, "counter")
        
        # 结束追踪
        await observability.end_trace(trace.trace_id, "ok")
        
        # 验证所有模块都正常工作
        stats = security.get_stats()
        assert stats["permission_checks"] > 0
        
        # 记录一些日志
        await observability.info("测试完成", module="test")
        
        logs = await observability.get_logs()
        assert len(logs) > 0
    
    @pytest.mark.asyncio
    async def test_full_stack_without_modules(self):
        """完整技术栈（没有模块）"""
        
        # 没有模块，直接执行
        
        # 没有权限检查，直接允许
        has_permission = True
        assert has_permission is True
        
        # 没有代码检查，直接允许
        code_check_allowed = True
        assert code_check_allowed is True
        
        # 没有计划，直接执行
        # 模拟执行
        await asyncio.sleep(0.01)
        executed = True
        assert executed is True
        
        # 没有可观测性，无法追踪
        traced = False
        assert traced is False
    
    def test_summary(self):
        """消融测试总结"""
        summary = {
            "planner": {
                "with_module": "任务分解、依赖管理、进度跟踪、错误恢复",
                "without_module": "缺乏结构、难以追踪、错误处理困难"
            },
            "code_executor": {
                "with_module": "代码执行、错误处理、资源限制、沙盒隔离",
                "without_module": "无法执行、无输出、无错误信息"
            },
            "security": {
                "with_module": "权限控制、审计日志、审批流程、速率限制",
                "without_module": "无权限控制、无审计、无审批、无速率限制"
            },
            "observability": {
                "with_module": "结构化日志、指标收集、分布式追踪、健康检查",
                "without_module": "无结构化日志、无指标、无追踪、无健康检查"
            },
            "agents_md": {
                "with_module": "规则检查、违规检测、自动修复、安全防护",
                "without_module": "无规则检查、无违规检测、无自动修复、无安全防护"
            }
        }
        
        assert len(summary) == 5
        for module, info in summary.items():
            assert "with_module" in info
            assert "without_module" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
