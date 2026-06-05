# planner/api.py

"""
规划器 API 端点

提供 RESTful API 接口。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .core import Planner
from .models import Plan, PlanStatus, StepStatus


class PlannerAPI:
    """
    规划器 API
    
    提供以下端点：
    - POST /api/planner/create: 创建执行计划
    - POST /api/planner/decompose: 分解任务
    - POST /api/planner/validate: 验证计划
    - POST /api/planner/optimize: 优化计划
    - POST /api/planner/replan: 重新规划
    - GET /api/planner/plans/{plan_id}: 获取计划详情
    """
    
    def __init__(self, planner: Planner):
        """
        初始化 API
        
        Args:
            planner: 规划器实例
        """
        self.planner = planner
    
    async def handle_create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理创建计划请求
        
        POST /api/planner/create
        
        Request Body:
        {
            "task": "任务描述",
            "context": {},
            "strategy": "sequential",
            "max_steps": 20
        }
        """
        task = data.get("task")
        if not task:
            return {"error": "任务描述不能为空", "status": 400}
        
        context = data.get("context", {})
        strategy = data.get("strategy", "sequential")
        max_steps = data.get("max_steps", 20)
        
        try:
            plan = await self.planner.create_plan(
                task=task,
                context=context,
                strategy=strategy,
                max_steps=max_steps
            )
            
            return {
                "success": True,
                "plan": plan.to_dict(),
                "status": 200
            }
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    async def handle_decompose(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理分解任务请求
        
        POST /api/planner/decompose
        
        Request Body:
        {
            "task": "任务描述",
            "strategy": "sequential"
        }
        """
        task = data.get("task")
        if not task:
            return {"error": "任务描述不能为空", "status": 400}
        
        strategy = data.get("strategy", "sequential")
        
        try:
            steps = await self.planner.decompose_task(task, strategy)
            
            return {
                "success": True,
                "steps": [step.to_dict() for step in steps],
                "count": len(steps),
                "status": 200
            }
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    async def handle_validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理验证计划请求
        
        POST /api/planner/validate
        
        Request Body:
        {
            "plan": {}
        }
        """
        plan_data = data.get("plan")
        if not plan_data:
            return {"error": "计划数据不能为空", "status": 400}
        
        try:
            plan = Plan.from_dict(plan_data)
            result = self.planner.validate_plan(plan)
            
            return {
                "success": True,
                "validation": result.to_dict(),
                "status": 200
            }
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    async def handle_optimize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理优化计划请求
        
        POST /api/planner/optimize
        
        Request Body:
        {
            "plan": {}
        }
        """
        plan_data = data.get("plan")
        if not plan_data:
            return {"error": "计划数据不能为空", "status": 400}
        
        try:
            plan = Plan.from_dict(plan_data)
            optimized = self.planner.optimize_plan(plan)
            
            return {
                "success": True,
                "plan": optimized.to_dict(),
                "status": 200
            }
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    async def handle_replan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理重新规划请求
        
        POST /api/planner/replan
        
        Request Body:
        {
            "plan_id": "plan_xxx",
            "feedback": "反馈信息",
            "error": "错误信息"
        }
        """
        plan_id = data.get("plan_id")
        if not plan_id:
            return {"error": "计划 ID 不能为空", "status": 400}
        
        feedback = data.get("feedback")
        error = data.get("error")
        
        try:
            new_plan = await self.planner.replan(plan_id, feedback, error)
            
            return {
                "success": True,
                "plan": new_plan.to_dict(),
                "status": 200
            }
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    async def handle_get_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        处理获取计划请求
        
        GET /api/planner/plans/{plan_id}
        """
        plan = self.planner.get_plan(plan_id)
        if plan is None:
            return {"error": "计划不存在", "status": 404}
        
        return {
            "success": True,
            "plan": plan.to_dict(),
            "status": 200
        }
    
    async def handle_list_plans(self, status: Optional[str] = None) -> Dict[str, Any]:
        """
        处理列出计划请求
        
        GET /api/planner/plans?status=draft
        """
        plan_status = None
        if status:
            try:
                plan_status = PlanStatus(status)
            except ValueError:
                return {"error": f"无效的状态: {status}", "status": 400}
        
        plans = self.planner.list_plans(plan_status)
        
        return {
            "success": True,
            "plans": [p.to_dict() for p in plans],
            "count": len(plans),
            "status": 200
        }
    
    async def handle_update_step(self, plan_id: str, step_id: str,
                                data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理更新步骤状态请求
        
        POST /api/planner/plans/{plan_id}/steps/{step_id}
        
        Request Body:
        {
            "status": "completed",
            "result": {},
            "error": null
        }
        """
        status_str = data.get("status")
        if not status_str:
            return {"error": "状态不能为空", "status": 400}
        
        try:
            status = StepStatus(status_str)
        except ValueError:
            return {"error": f"无效的状态: {status_str}", "status": 400}
        
        result = data.get("result")
        error = data.get("error")
        
        success = self.planner.update_step_status(
            plan_id=plan_id,
            step_id=step_id,
            status=status,
            result=result,
            error=error
        )
        
        if success:
            return {"success": True, "status": 200}
        else:
            return {"error": "更新失败", "status": 400}
    
    def get_routes(self) -> Dict[str, Any]:
        """
        获取路由配置
        
        Returns:
            路由字典
        """
        return {
            "POST /api/planner/create": self.handle_create,
            "POST /api/planner/decompose": self.handle_decompose,
            "POST /api/planner/validate": self.handle_validate,
            "POST /api/planner/optimize": self.handle_optimize,
            "POST /api/planner/replan": self.handle_replan,
            "GET /api/planner/plans/{plan_id}": self.handle_get_plan,
            "GET /api/planner/plans": self.handle_list_plans,
            "POST /api/planner/plans/{plan_id}/steps/{step_id}": self.handle_update_step
        }
