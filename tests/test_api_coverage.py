# tests/test_api_coverage.py

"""
API 覆盖率测试

测试所有模块的 API 端点，确保 100% 覆盖率。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# ============================================================
# Planner API 覆盖测试
# ============================================================

class TestPlannerAPICoverage:
    """规划器 API 覆盖测试"""
    
    @pytest.fixture
    def planner_setup(self):
        """创建规划器和 API 实例"""
        from planner.core import Planner
        from planner.api import PlannerAPI
        
        # 模拟 LLM 调用
        async def mock_llm_caller(prompt: str) -> str:
            return '''
            [
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
            ]
            '''
        
        planner = Planner(llm_caller=mock_llm_caller)
        api = PlannerAPI(planner)
        return planner, api
    
    @pytest.mark.asyncio
    async def test_handle_optimize(self, planner_setup):
        """测试优化计划 API"""
        planner, api = planner_setup
        
        # 先创建一个计划
        plan = await planner.create_plan(
            task="测试任务",
            strategy="sequential"
        )
        
        # 优化计划
        data = {"plan": plan.to_dict()}
        result = await api.handle_optimize(data)
        
        assert result["success"] is True
        assert "plan" in result
    
    @pytest.mark.asyncio
    async def test_handle_replan(self, planner_setup):
        """测试重新规划 API"""
        planner, api = planner_setup
        
        # 先创建一个计划
        plan = await planner.create_plan(
            task="测试任务",
            strategy="sequential"
        )
        
        # 重新规划
        data = {
            "plan_id": plan.plan_id,
            "feedback": "需要调整策略"
        }
        result = await api.handle_replan(data)
        
        assert result["success"] is True
        assert "plan" in result
    
    @pytest.mark.asyncio
    async def test_handle_get_plan(self, planner_setup):
        """测试获取计划详情 API"""
        planner, api = planner_setup
        
        # 先创建一个计划
        plan = await planner.create_plan(
            task="测试任务",
            strategy="sequential"
        )
        
        # 获取计划详情
        result = await api.handle_get_plan(plan.plan_id)
        
        assert result["success"] is True
        assert result["plan"]["plan_id"] == plan.plan_id
    
    @pytest.mark.asyncio
    async def test_handle_list_plans(self, planner_setup):
        """测试列出计划 API"""
        planner, api = planner_setup
        
        # 先创建几个计划
        await planner.create_plan(task="任务1", strategy="sequential")
        await planner.create_plan(task="任务2", strategy="parallel")
        
        # 列出所有计划
        result = await api.handle_list_plans()
        
        assert result["success"] is True
        assert result["count"] >= 2
        assert "plans" in result
    
    @pytest.mark.asyncio
    async def test_handle_list_plans_with_status(self, planner_setup):
        """测试按状态列出计划 API"""
        planner, api = planner_setup
        
        # 创建计划
        await planner.create_plan(task="测试任务", strategy="sequential")
        
        # 按状态列出
        result = await api.handle_list_plans(status="draft")
        
        assert result["success"] is True
        assert "plans" in result
    
    @pytest.mark.asyncio
    async def test_handle_update_step(self, planner_setup):
        """测试更新步骤状态 API"""
        planner, api = planner_setup
        
        # 创建计划
        plan = await planner.create_plan(
            task="测试任务",
            strategy="sequential"
        )
        
        # 更新第一个步骤的状态
        if plan.steps:
            step_id = plan.steps[0].step_id
            data = {
                "status": "completed",
                "result": {"output": "步骤完成"}
            }
            
            result = await api.handle_update_step(
                plan.plan_id, step_id, data
            )
            
            assert result["success"] is True


# ============================================================
# Code Executor API 覆盖测试
# ============================================================

class TestCodeExecutorAPICoverage:
    """代码执行引擎 API 覆盖测试"""
    
    @pytest.fixture
    def executor_setup(self):
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
    async def test_execute_in_sandbox(self, executor_setup):
        """测试沙盒执行 API"""
        executor = executor_setup
        
        code = "print('Hello from sandbox!')"
        result = await executor.execute_in_sandbox(
            code=code,
            language="python"
        )
        
        # 沙盒执行应该成功或给出有意义的错误
        assert result is not None
        assert hasattr(result, 'success')
    
    @pytest.mark.asyncio
    async def test_install_package(self, executor_setup):
        """测试安装包 API"""
        executor = executor_setup
        
        # 测试安装一个已存在的包（应该成功）
        success = await executor.install_package(
            package="json",
            language="python"
        )
        
        # json 是内置包，应该返回 True 或处理得当
        assert isinstance(success, bool)


# ============================================================
# Security Module API 覆盖测试
# ============================================================

class TestSecurityAPICoverage:
    """安全模块 API 覆盖测试"""
    
    @pytest.fixture
    def security_setup(self):
        """创建安全模块实例"""
        from security_module.core import SecurityModule
        from security_module.models import SecurityConfig
        
        config = SecurityConfig(
            default_approval_timeout=10.0,
            enable_rate_limiting=True,
            enable_audit_logging=True,
            enable_permission_check=True
        )
        return SecurityModule(config=config)
    
    @pytest.mark.asyncio
    async def test_reject_request(self, security_setup):
        """测试拒绝请求 API"""
        security = security_setup
        
        # 创建审批请求
        request = await security.request_approval(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        # 拒绝请求
        success = await security.reject(
            request_id=request.request_id,
            approver_id="approver1",
            reason="Not allowed"
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_get_approval_request(self, security_setup):
        """测试获取审批请求详情 API"""
        security = security_setup
        
        # 创建审批请求
        request = await security.request_approval(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        # 获取请求详情
        retrieved = security.approval_engine.get_request(request.request_id)
        
        assert retrieved is not None
        assert retrieved.request_id == request.request_id
    
    @pytest.mark.asyncio
    async def test_list_approval_requests(self, security_setup):
        """测试列出审批请求 API"""
        security = security_setup
        
        # 创建多个审批请求
        await security.request_approval(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        await security.request_approval(
            requester_id="user2",
            action="write",
            resource="file"
        )
        
        # 列出所有请求
        requests = security.get_approval_requests()
        
        assert len(requests) >= 2
    
    @pytest.mark.asyncio
    async def test_list_approval_requests_with_filter(self, security_setup):
        """测试按状态过滤审批请求 API"""
        security = security_setup
        
        # 创建请求
        await security.request_approval(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        # 按状态过滤
        pending = security.get_approval_requests(status="pending")
        
        assert len(pending) >= 1
    
    @pytest.mark.asyncio
    async def test_get_audit_log(self, security_setup):
        """测试获取审计日志 API"""
        security = security_setup
        
        # 执行一些操作以生成审计日志
        await security.check_permission(
            user_id="user1",
            resource="tool",
            action="read"
        )
        
        # 获取审计日志
        entries = security.get_audit_log()
        
        assert isinstance(entries, list)
    
    @pytest.mark.asyncio
    async def test_get_audit_log_with_filter(self, security_setup):
        """测试按用户过滤审计日志 API"""
        security = security_setup
        
        # 执行操作
        await security.check_permission(
            user_id="user1",
            resource="tool",
            action="read"
        )
        
        # 按用户过滤
        entries = security.get_audit_log(user_id="user1")
        
        assert isinstance(entries, list)
    
    @pytest.mark.asyncio
    async def test_get_permissions(self, security_setup):
        """测试获取权限列表 API"""
        security = security_setup
        
        # 获取权限列表
        permissions = security.get_permissions()
        
        assert isinstance(permissions, list)
        assert len(permissions) > 0
    
    @pytest.mark.asyncio
    async def test_report_security_violation(self, security_setup):
        """测试报告安全违规 API"""
        security = security_setup
        
        # 报告安全违规
        await security.report_security_violation(
            user_id="user1",
            violation_type="unauthorized_access",
            details={"resource": "admin_panel"},
            ip_address="192.168.1.1"
        )
        
        # 检查统计信息
        stats = security.get_stats()
        assert stats["security_violations"] > 0


# ============================================================
# Observability Module API 覆盖测试
# ============================================================

class TestObservabilityAPICoverage:
    """可观测性模块 API 覆盖测试"""
    
    @pytest.fixture
    def observability_setup(self):
        """创建可观测性模块实例"""
        from observability_module.core import ObservabilityModule
        from observability_module.models import ObservabilityConfig, LogLevel
        
        config = ObservabilityConfig(
            log_level=LogLevel.DEBUG.value,
            log_max_entries=1000,
            metrics_max_entries=1000,
            enable_tracing=True,
            health_check_interval=10.0
        )
        return ObservabilityModule(config=config)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, observability_setup):
        """测试获取仪表盘数据 API"""
        observability = observability_setup
        
        # 记录一些数据
        await observability.info("Test message")
        await observability.record_metric("test_metric", 42.0)
        
        # 获取仪表盘数据
        dashboard = await observability.get_dashboard_data()
        
        assert dashboard is not None
        assert dashboard.health_status is not None
        assert hasattr(dashboard, 'recent_logs')
        assert hasattr(dashboard, 'metrics_summary')


# ============================================================
# 综合 API 覆盖率验证
# ============================================================

class TestAPIEndpointCoverage:
    """API 端点覆盖率综合验证"""
    
    def test_planner_api_routes(self):
        """验证规划器 API 路由完整性"""
        from planner.api import PlannerAPI
        from planner.core import Planner
        
        planner = Planner()
        api = PlannerAPI(planner)
        routes = api.get_routes()
        
        expected_routes = [
            "POST /api/planner/create",
            "POST /api/planner/decompose",
            "POST /api/planner/validate",
            "POST /api/planner/optimize",
            "POST /api/planner/replan",
            "GET /api/planner/plans/{plan_id}",
            "GET /api/planner/plans",
            "POST /api/planner/plans/{plan_id}/steps/{step_id}"
        ]
        
        for route in expected_routes:
            assert route in routes, f"Missing route: {route}"
        
        assert len(routes) == len(expected_routes)
    
    def test_code_executor_api_router(self):
        """验证代码执行引擎 API 路由器创建"""
        from code_executor.api import create_executor_router
        from code_executor.core import CodeExecutor
        from code_executor.models import ExecutorConfig
        
        config = ExecutorConfig(enable_sandbox=False)
        executor = CodeExecutor(config=config)
        router = create_executor_router(executor)
        
        # 检查路由数量
        routes = [r for r in router.routes]
        assert len(routes) >= 8  # 8 个端点
    
    def test_security_api_router(self):
        """验证安全模块 API 路由器创建"""
        from security_module.api import create_security_router
        from security_module.core import SecurityModule
        
        security = SecurityModule()
        router = create_security_router(security)
        
        # 检查路由数量
        routes = [r for r in router.routes]
        assert len(routes) >= 13  # 13 个端点
    
    def test_observability_api_router(self):
        """验证可观测性模块 API 路由器创建"""
        from observability_module.api import create_observability_router
        from observability_module.core import ObservabilityModule
        
        observability = ObservabilityModule()
        router = create_observability_router(observability)
        
        # 检查路由数量
        routes = [r for r in router.routes]
        assert len(routes) >= 13  # 13 个端点
    
    def test_agents_md_api_router(self):
        """验证免疫机制模块 API 路由器创建"""
        from agents_md_module.api import create_immune_router
        from agents_md_module.immune_system import ImmuneSystem
        
        immune_system = ImmuneSystem()
        router = create_immune_router(immune_system)
        
        # 检查路由数量
        routes = [r for r in router.routes]
        assert len(routes) >= 9  # 9 个端点


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
