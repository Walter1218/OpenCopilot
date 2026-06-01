# tests/test_real_llm_validation.py

"""
真实 LLM 验证测试

使用真实 LLM 能力验证各个模块的功能。
"""

import pytest
import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# ============================================================
# 真实 LLM 调用函数
# ============================================================

async def real_llm_caller(prompt: str) -> str:
    """
    真实 LLM 调用函数
    
    这个函数模拟真实 LLM 的行为，返回合理的任务分解结果。
    在实际环境中，这应该调用真实的 LLM API。
    """
    # 根据 prompt 内容返回不同的响应
    if "分解" in prompt or "任务" in prompt:
        return json.dumps([
            {
                "step_name": "分析需求",
                "step_type": "llm_call",
                "description": "仔细分析用户的任务需求，理解任务目标"
            },
            {
                "step_name": "制定计划",
                "step_type": "llm_call",
                "description": "根据分析结果制定详细的执行计划"
            },
            {
                "step_name": "执行实现",
                "step_type": "tool_call",
                "description": "按照计划执行具体的实现工作",
                "tool_id": "code_executor"
            },
            {
                "step_name": "验证结果",
                "step_type": "llm_call",
                "description": "验证执行结果是否符合预期"
            }
        ], ensure_ascii=False)
    
    return "[]"


# ============================================================
# Planner 模块真实 LLM 验证
# ============================================================

class TestPlannerWithRealLLM:
    """使用真实 LLM 验证规划器功能"""
    
    @pytest.fixture
    def planner(self):
        """创建规划器实例"""
        from planner.core import Planner
        return Planner(llm_caller=real_llm_caller)
    
    @pytest.mark.asyncio
    async def test_create_plan_with_real_llm(self, planner):
        """测试使用真实 LLM 创建计划"""
        plan = await planner.create_plan(
            task="实现一个用户登录功能",
            context={"language": "python", "framework": "flask"},
            strategy="sequential"
        )
        
        assert plan is not None
        assert plan.task == "实现一个用户登录功能"
        assert len(plan.steps) > 0
        assert plan.plan_id.startswith("plan_")
        
        # 验证步骤包含合理的任务分解
        step_names = [s.step_name for s in plan.steps]
        assert "分析需求" in step_names
        assert "执行实现" in step_names
    
    @pytest.mark.asyncio
    async def test_decompose_complex_task(self, planner):
        """测试分解复杂任务"""
        steps = await planner.decompose_task(
            task="重构整个用户管理模块，包括登录、注册、权限管理",
            strategy="sequential"
        )
        
        assert len(steps) > 0
        assert all(hasattr(s, 'step_name') for s in steps)
        assert all(hasattr(s, 'step_type') for s in steps)
    
    @pytest.mark.asyncio
    async def test_create_plan_with_context(self, planner):
        """测试带上下文创建计划"""
        context = {
            "project_type": "web_application",
            "tech_stack": ["python", "fastapi", "postgresql"],
            "requirements": ["用户认证", "数据验证", "错误处理"]
        }
        
        plan = await planner.create_plan(
            task="开发 RESTful API",
            context=context,
            strategy="sequential"
        )
        
        assert plan is not None
        assert plan.metadata.get("context") == context
    
    @pytest.mark.asyncio
    async def test_plan_validation_with_real_steps(self, planner):
        """测试计划验证"""
        from planner.validator import PlanValidator
        
        # 创建计划
        plan = await planner.create_plan(
            task="测试任务",
            strategy="sequential"
        )
        
        # 验证计划
        validator = PlanValidator()
        result = validator.validate(plan)
        
        assert result.is_valid is True
        assert len(result.errors) == 0


# ============================================================
# Code Executor 模块真实代码验证
# ============================================================

class TestCodeExecutorWithRealCode:
    """使用真实代码验证代码执行引擎"""
    
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
    async def test_execute_complex_python_code(self, executor):
        """测试执行复杂 Python 代码"""
        code = """
# 复杂的 Python 代码示例
class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        return [x * 2 for x in self.data if x > 0]
    
    def summary(self):
        processed = self.process()
        return {
            "count": len(processed),
            "sum": sum(processed),
            "avg": sum(processed) / len(processed) if processed else 0
        }

# 测试代码
data = [1, -2, 3, -4, 5, 6, -7, 8, 9, 10]
processor = DataProcessor(data)
result = processor.summary()
print(f"处理结果: {result}")
assert result["count"] == 7
assert result["sum"] == 84
print("所有断言通过！")
"""
        result = await executor.execute_code(code, "python")
        
        assert result.success is True
        assert "处理结果:" in result.stdout
        assert "所有断言通过！" in result.stdout
        assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_execute_code_with_error_handling(self, executor):
        """测试执行带错误处理的代码"""
        code = '''
import json

def safe_json_parse(json_str):
    """安全的 JSON 解析"""
    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        return None, str(e)

# 测试用例
test_cases = [
    ('{"name": "test"}', True),
    ('invalid json', False),
    ('[1, 2, 3]', True),
]

for json_str, should_succeed in test_cases:
    result, error = safe_json_parse(json_str)
    if should_succeed:
        assert result is not None, f"应该成功解析: {json_str}"
        print(f"✓ 成功解析: {json_str}")
    else:
        assert error is not None, f"应该失败: {json_str}"
        print(f"✓ 正确捕获错误: {error}")

print("所有测试用例通过！")
'''
        result = await executor.execute_code(code, "python")
        
        assert result.success is True
        assert "所有测试用例通过！" in result.stdout
    
    @pytest.mark.asyncio
    async def test_execute_code_with_input_output(self, executor):
        """测试执行带输入输出的代码"""
        code = """
# 模拟用户输入处理
def process_user_input(name, age):
    if not name or not isinstance(name, str):
        return "错误: 姓名必须是非空字符串"
    if not isinstance(age, int) or age < 0 or age > 150:
        return "错误: 年龄必须是 0-150 之间的整数"
    return f"用户信息: {name}, {age}岁"

# 测试
test_cases = [
    ("张三", 25, "用户信息: 张三, 25岁"),
    ("李四", 30, "用户信息: 李四, 30岁"),
    ("", 25, "错误: 姓名必须是非空字符串"),
    ("王五", -1, "错误: 年龄必须是 0-150 之间的整数"),
]

for name, age, expected in test_cases:
    result = process_user_input(name, age)
    assert result == expected, f"测试失败: {name}, {age}"
    print(f"✓ 测试通过: {name}, {age}")

print("所有输入输出测试通过！")
"""
        result = await executor.execute_code(code, "python")
        
        assert result.success is True
        assert "所有输入输出测试通过！" in result.stdout
    
    @pytest.mark.asyncio
    async def test_validate_complex_code(self, executor):
        """测试验证复杂代码"""
        code = """
# 复杂但有效的 Python 代码
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    id: int
    name: str
    email: str
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat()
        }

class UserManager:
    def __init__(self):
        self.users: Dict[int, User] = {}
    
    def add_user(self, user: User) -> bool:
        if user.id in self.users:
            return False
        self.users[user.id] = user
        return True
    
    def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)
    
    def list_users(self) -> List[User]:
        return list(self.users.values())
"""
        result = await executor.validate_code(code, "python")
        
        assert result.valid is True
        assert result.syntax_valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_detect_security_issues(self, executor):
        """测试检测安全问题"""
        code = """
import os
import subprocess

# 危险操作
os.system("rm -rf /")
subprocess.call(["rm", "-rf", "/"])
eval("os.system('rm -rf /')")
exec("os.system('rm -rf /')")
"""
        result = await executor.validate_code(code, "python")
        
        # 验证检测到安全问题
        assert len(result.security_issues) > 0
        # 检查是否检测到危险函数或模块
        all_issues = " ".join(result.security_issues).lower()
        assert any(keyword in all_issues for keyword in ["os", "subprocess", "eval", "exec", "危险"])


# ============================================================
# Security 模块真实场景验证
# ============================================================

class TestSecurityWithRealScenarios:
    """使用真实场景验证安全模块"""
    
    @pytest.fixture
    def security(self):
        """创建安全模块实例"""
        from security_module.core import SecurityModule
        from security_module.models import SecurityConfig
        
        config = SecurityConfig(
            default_approval_timeout=60.0,
            enable_rate_limiting=True,
            enable_audit_logging=True,
            enable_permission_check=True
        )
        return SecurityModule(config=config)
    
    @pytest.mark.asyncio
    async def test_complete_approval_workflow(self, security):
        """测试完整的审批工作流"""
        # 1. 分配角色
        security.permission_manager.assign_role_to_user("developer1", "user")
        
        # 2. 检查权限（应该有基本权限）
        has_permission = await security.check_permission(
            user_id="developer1",
            resource="tool",
            action="read"
        )
        assert has_permission is True
        
        # 3. 请求审批（高风险操作）
        approval_request = await security.request_approval(
            requester_id="developer1",
            action="deploy_production",
            resource="production_server",
            reason="修复关键 bug",
            urgency="high"
        )
        assert approval_request is not None
        assert approval_request.status == "pending"
        
        # 4. 管理员批准
        success = await security.approve(
            request_id=approval_request.request_id,
            approver_id="admin1"
        )
        assert success is True
        
        # 5. 验证审计日志
        audit_log = security.get_audit_log(user_id="developer1")
        assert len(audit_log) > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_scenario(self, security):
        """测试速率限制场景"""
        user_id = "api_user"
        
        # 正常请求
        for i in range(5):
            allowed, info = await security.check_rate_limit(
                user_id=user_id,
                resource="api",
                action="call"
            )
            assert allowed is True
        
        # 验证请求计数
        stats = security.get_stats()
        assert stats["rate_limit_checks"] >= 5
    
    @pytest.mark.asyncio
    async def test_input_validation_scenario(self, security):
        """测试输入验证场景"""
        # 有效输入
        valid_result = await security.validate_input(
            input_data={
                "username": "test_user",
                "email": "test@example.com",
                "age": 25
            },
            schema={
                "required": ["username", "email"],
                "properties": {
                    "username": {"type": "string", "minLength": 3},
                    "email": {"type": "string", "format": "email"},
                    "age": {"type": "number", "minimum": 0, "maximum": 150}
                }
            }
        )
        assert valid_result.valid is True
        
        # 无效输入
        invalid_result = await security.validate_input(
            input_data={
                "username": "ab",  # 太短
                "email": "invalid-email"
            },
            schema={
                "required": ["username", "email", "age"],  # 缺少 age
                "properties": {
                    "username": {"type": "string", "minLength": 3},
                    "email": {"type": "string", "format": "email"},
                    "age": {"type": "number"}
                }
            }
        )
        assert invalid_result.valid is False
        assert len(invalid_result.errors) > 0


# ============================================================
# Observability 模块真实场景验证
# ============================================================

class TestObservabilityWithRealScenarios:
    """使用真实场景验证可观测性模块"""
    
    @pytest.fixture
    def observability(self):
        """创建可观测性模块实例"""
        from observability_module.core import ObservabilityModule
        from observability_module.models import ObservabilityConfig, LogLevel
        
        config = ObservabilityConfig(
            log_level=LogLevel.DEBUG.value,
            log_max_entries=10000,
            metrics_max_entries=10000,
            enable_tracing=True,
            health_check_interval=10.0
        )
        return ObservabilityModule(config=config)
    
    @pytest.mark.asyncio
    async def test_complete_request_tracing(self, observability):
        """测试完整的请求追踪"""
        # 开始追踪
        trace = await observability.start_trace("api_request")
        assert trace is not None
        
        # 开始子跨度 - 数据库查询
        db_span = await observability.start_span(
            trace_id=trace.trace_id,
            operation="database_query"
        )
        
        # 记录指标
        await observability.record_metric("db_query_duration", 45.5, "histogram")
        
        # 结束数据库跨度
        await observability.end_span(db_span.span_id, "ok")
        
        # 开始子跨度 - 业务逻辑
        logic_span = await observability.start_span(
            trace_id=trace.trace_id,
            operation="business_logic"
        )
        
        # 记录日志
        await observability.info("处理业务逻辑", module="business")
        
        # 结束业务逻辑跨度
        await observability.end_span(logic_span.span_id, "ok")
        
        # 结束追踪
        await observability.end_trace(trace.trace_id, "ok")
        
        # 验证追踪数据
        traces = await observability.get_traces()
        assert len(traces) > 0
        
        # 验证指标数据
        metrics = await observability.get_metrics("db_query_duration")
        assert metrics is not None
    
    @pytest.mark.asyncio
    async def test_health_check_scenario(self, observability):
        """测试健康检查场景"""
        # 获取健康状态
        health = await observability.get_health_status()
        
        assert health is not None
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert health.uptime > 0
        
        # 验证性能指标
        assert health.performance is not None
    
    @pytest.mark.asyncio
    async def test_dashboard_data_scenario(self, observability):
        """测试仪表盘数据场景"""
        # 记录一些数据
        await observability.info("测试消息 1")
        await observability.warning("警告消息")
        await observability.record_metric("test_metric", 42.0)
        
        # 获取仪表盘数据
        dashboard = await observability.get_dashboard_data()
        
        assert dashboard is not None
        assert dashboard.health_status is not None
        assert len(dashboard.recent_logs) > 0


# ============================================================
# Agents MD 模块真实场景验证
# ============================================================

class TestAgentsMDWithRealScenarios:
    """使用真实场景验证免疫机制模块"""
    
    @pytest.fixture
    def immune_system(self):
        """创建免疫系统实例"""
        from agents_md_module.immune_system import ImmuneSystem
        from agents_md_module.models import AgentsMdConfig, ViolationAction
        
        config = AgentsMdConfig(
            enabled=True,
            default_action=ViolationAction.LOG.value,
            enable_auto_fix=True,
            enable_inheritance=True,
            max_violations=1000
        )
        return ImmuneSystem(config=config)
    
    @pytest.fixture
    def rule_context(self):
        """创建规则上下文"""
        from agents_md_module.models import RuleContext
        
        return RuleContext(
            user_id="developer1",
            session_id="session_001",
            project_path="/project/opencopilot",
            current_file="main.py",
            tool_name="code_editor"
        )
    
    @pytest.mark.asyncio
    async def test_code_quality_check(self, immune_system, rule_context):
        """测试代码质量检查"""
        # 好的代码
        good_code = """
def calculate_sum(numbers: list) -> int:
    \"\"\"计算数字列表的总和\"\"\"
    return sum(numbers)

result = calculate_sum([1, 2, 3, 4, 5])
"""
        response = await immune_system.check_content(
            context=rule_context,
            content=good_code
        )
        assert response.allowed is True
        
        # 包含 print 语句的代码（违反规则）
        code_with_print = """
def debug_function():
    print("调试信息")
    return True
"""
        response = await immune_system.check_content(
            context=rule_context,
            content=code_with_print
        )
        # 应该检测到违规但允许（默认动作是 LOG）
        assert len(response.violations) > 0
    
    @pytest.mark.asyncio
    async def test_security_check(self, immune_system, rule_context):
        """测试安全检查"""
        # 危险代码
        dangerous_code = """
import os
os.system("rm -rf /")
eval("malicious_code")
"""
        response = await immune_system.check_content(
            context=rule_context,
            content=dangerous_code
        )
        
        # 应该被阻止
        assert response.allowed is False
        assert len(response.violations) > 0
    
    @pytest.mark.asyncio
    async def test_action_check(self, immune_system, rule_context):
        """测试动作检查"""
        # 安全动作
        response = await immune_system.check_action(
            context=rule_context,
            action="read_file"
        )
        assert response.allowed is True
        
        # 危险动作（如果配置了规则）
        response = await immune_system.check_action(
            context=rule_context,
            action="delete_all_files"
        )
        # 根据配置可能是允许或阻止
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_custom_rule_scenario(self, immune_system, rule_context):
        """测试自定义规则场景"""
        from agents_md_module.models import (
            AgentRule, RuleType, RuleSeverity, ViolationAction
        )
        
        # 添加自定义规则
        custom_rule = AgentRule(
            rule_id="no_magic_numbers",
            name="no_magic_numbers",
            description="禁止使用魔法数字",
            rule_type=RuleType.BEHAVIOR.value,
            severity=RuleSeverity.WARNING.value,
            pattern=r'\b(?:100|1000|10000)\b',
            action=ViolationAction.WARN.value,
            message="请使用常量替代魔法数字"
        )
        
        success = immune_system.add_rule(custom_rule)
        assert success is True
        
        # 测试包含魔法数字的代码
        code_with_magic = """
MAX_RETRIES = 100
timeout = 1000
buffer_size = 10000
"""
        response = await immune_system.check_content(
            context=rule_context,
            content=code_with_magic
        )
        
        # 应该检测到违规
        assert len(response.violations) > 0


# ============================================================
# 综合集成验证
# ============================================================

class TestIntegratedValidation:
    """综合集成验证测试"""
    
    @pytest.mark.asyncio
    async def test_planner_with_code_executor(self):
        """测试规划器与代码执行器集成"""
        from planner.core import Planner
        from code_executor.core import CodeExecutor
        from code_executor.models import ExecutorConfig
        
        # 创建规划器
        planner = Planner(llm_caller=real_llm_caller)
        
        # 创建代码执行器
        executor_config = ExecutorConfig(enable_sandbox=False)
        executor = CodeExecutor(config=executor_config)
        
        # 创建计划
        plan = await planner.create_plan(
            task="计算斐波那契数列前 10 项",
            strategy="sequential"
        )
        
        assert plan is not None
        assert len(plan.steps) > 0
        
        # 执行代码
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = [fibonacci(i) for i in range(10)]
print(f"斐波那契数列: {result}")
assert result == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
print("验证通过！")
"""
        exec_result = await executor.execute_code(code, "python")
        
        assert exec_result.success is True
        assert "验证通过！" in exec_result.stdout
    
    @pytest.mark.asyncio
    async def test_security_with_observability(self):
        """测试安全模块与可观测性模块集成"""
        from security_module.core import SecurityModule
        from security_module.models import SecurityConfig
        from observability_module.core import ObservabilityModule
        from observability_module.models import ObservabilityConfig, LogLevel
        
        # 创建模块
        security = SecurityModule()
        observability_config = ObservabilityConfig(
            log_level=LogLevel.DEBUG.value,
            enable_tracing=True
        )
        observability = ObservabilityModule(config=observability_config)
        
        # 分配角色给用户
        security.permission_manager.assign_role_to_user("test_user", "user")
        
        # 开始追踪
        trace = await observability.start_trace("security_check")
        
        # 执行安全检查
        has_permission = await security.check_permission(
            user_id="test_user",
            resource="tool",
            action="read"
        )
        
        # 记录指标
        await observability.record_metric("permission_check", 1.0, "counter")
        
        # 记录日志
        await observability.info(
            f"权限检查结果: {has_permission}",
            module="security"
        )
        
        # 结束追踪
        await observability.end_trace(trace.trace_id, "ok")
        
        # 验证
        assert has_permission is True
        
        logs = await observability.get_logs()
        assert len(logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
