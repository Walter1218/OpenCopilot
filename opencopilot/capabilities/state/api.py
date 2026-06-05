"""
状态管理 API 模块

提供 RESTful API 端点，用于状态管理功能。
可以集成到 smart_copilot_api.py 中。
"""

import json
import time
from typing import Dict, Any, Optional
from http.server import BaseHTTPRequestHandler
import threading

from .core import StateManager, TaskStatus
from .checkpoint import CheckpointManager
from .recovery import RecoveryManager, RecoveryConfig, RecoveryStrategy


class StateManagerAPI:
    """
    状态管理 API
    
    提供以下端点：
    - GET  /api/state/session/{session_id} - 获取会话状态
    - POST /api/state/session/{session_id} - 更新会话状态
    - GET  /api/state/task/{task_id} - 获取任务状态
    - POST /api/state/task - 创建任务
    - PUT  /api/state/task/{task_id} - 更新任务状态
    - GET  /api/state/tasks/{session_id} - 获取会话任务列表
    - POST /api/state/checkpoint - 创建检查点
    - GET  /api/state/checkpoint/{checkpoint_id} - 获取检查点
    - POST /api/state/recover/{task_id} - 恢复任务
    - GET  /api/state/statistics - 获取统计信息
    """
    
    def __init__(self, db_path: str = "asu_agent.db"):
        """
        初始化 API
        
        Args:
            db_path: 数据库路径
        """
        self.state_manager = StateManager(db_path)
        self.checkpoint_manager = CheckpointManager(db_path)
        self.recovery_manager = RecoveryManager(
            checkpoint_manager=self.checkpoint_manager,
            state_manager=self.state_manager
        )
    
    def handle_request(self, handler: BaseHTTPRequestHandler, method: str, path: str, body: Optional[Dict] = None) -> Dict[str, Any]:
        """
        处理 API 请求
        
        Args:
            handler: HTTP 请求处理器
            method: HTTP 方法
            path: 请求路径
            body: 请求体
            
        Returns:
            响应数据
        """
        try:
            # 解析路径
            parts = path.strip("/").split("/")
            
            if len(parts) < 3 or parts[0] != "api" or parts[1] != "state":
                return {"error": "无效的 API 路径", "status": 400}
            
            resource = parts[2]
            
            # 路由到对应的处理函数
            if resource == "session":
                return self._handle_session(method, parts[3:] if len(parts) > 3 else [], body)
            elif resource == "task":
                return self._handle_task(method, parts[3:] if len(parts) > 3 else [], body)
            elif resource == "tasks":
                return self._handle_tasks(method, parts[3:] if len(parts) > 3 else [], body)
            elif resource == "checkpoint":
                return self._handle_checkpoint(method, parts[3:] if len(parts) > 3 else [], body)
            elif resource == "recover":
                return self._handle_recover(method, parts[3:] if len(parts) > 3 else [], body)
            elif resource == "statistics":
                return self._handle_statistics(method)
            else:
                return {"error": f"未知的资源: {resource}", "status": 404}
        
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    def _handle_session(self, method: str, path_parts: list, body: Optional[Dict]) -> Dict[str, Any]:
        """处理会话相关请求"""
        if not path_parts:
            return {"error": "缺少会话ID", "status": 400}
        
        session_id = path_parts[0]
        
        if method == "GET":
            # 获取会话状态
            state = self.state_manager.get_session_state(session_id)
            return {"status": 200, "data": state.to_dict()}
        
        elif method == "POST":
            # 更新会话状态
            if not body:
                return {"error": "缺少请求体", "status": 400}
            
            state = self.state_manager.update_session_state(
                session_id,
                persona=body.get("persona"),
                is_active=body.get("is_active"),
                metadata=body.get("metadata")
            )
            return {"status": 200, "data": state.to_dict()}
        
        else:
            return {"error": f"不支持的 HTTP 方法: {method}", "status": 405}
    
    def _handle_task(self, method: str, path_parts: list, body: Optional[Dict]) -> Dict[str, Any]:
        """处理任务相关请求"""
        if method == "POST":
            # 创建任务
            if not body:
                return {"error": "缺少请求体", "status": 400}
            
            session_id = body.get("session_id")
            if not session_id:
                return {"error": "缺少 session_id", "status": 400}
            
            task = self.state_manager.create_task(
                session_id=session_id,
                task_type=body.get("task_type", "default"),
                description=body.get("description", ""),
                metadata=body.get("metadata")
            )
            return {"status": 201, "data": task.to_dict()}
        
        elif method in ["GET", "PUT"]:
            if not path_parts:
                return {"error": "缺少任务ID", "status": 400}
            
            task_id = path_parts[0]
            
            if method == "GET":
                # 获取任务状态
                task = self.state_manager.get_task(task_id)
                if not task:
                    return {"error": "任务不存在", "status": 404}
                return {"status": 200, "data": task.to_dict()}
            
            elif method == "PUT":
                # 更新任务状态
                if not body:
                    return {"error": "缺少请求体", "status": 400}
                
                status = None
                if "status" in body:
                    try:
                        status = TaskStatus(body["status"])
                    except ValueError:
                        return {"error": f"无效的任务状态: {body['status']}", "status": 400}
                
                task = self.state_manager.update_task(
                    task_id,
                    status=status,
                    progress=body.get("progress"),
                    result=body.get("result"),
                    error=body.get("error"),
                    metadata=body.get("metadata")
                )
                
                if not task:
                    return {"error": "任务不存在", "status": 404}
                
                return {"status": 200, "data": task.to_dict()}
        
        else:
            return {"error": f"不支持的 HTTP 方法: {method}", "status": 405}
    
    def _handle_tasks(self, method: str, path_parts: list, body: Optional[Dict]) -> Dict[str, Any]:
        """处理任务列表请求"""
        if method != "GET":
            return {"error": f"不支持的 HTTP 方法: {method}", "status": 405}
        
        if not path_parts:
            return {"error": "缺少会话ID", "status": 400}
        
        session_id = path_parts[0]
        
        # 获取查询参数
        status_filter = None
        limit = 100
        
        if body:
            if "status" in body:
                try:
                    status_filter = TaskStatus(body["status"])
                except ValueError:
                    pass
            if "limit" in body:
                limit = min(body["limit"], 1000)
        
        tasks = self.state_manager.get_session_tasks(session_id, status=status_filter, limit=limit)
        
        return {
            "status": 200,
            "data": {
                "session_id": session_id,
                "tasks": [t.to_dict() for t in tasks],
                "count": len(tasks)
            }
        }
    
    def _handle_checkpoint(self, method: str, path_parts: list, body: Optional[Dict]) -> Dict[str, Any]:
        """处理检查点相关请求"""
        if method == "POST":
            # 创建检查点
            if not body:
                return {"error": "缺少请求体", "status": 400}
            
            task_id = body.get("task_id")
            session_id = body.get("session_id")
            state_snapshot = body.get("state_snapshot")
            
            if not task_id or not session_id or not state_snapshot:
                return {"error": "缺少必要参数", "status": 400}
            
            checkpoint = self.checkpoint_manager.create_checkpoint(
                task_id=task_id,
                session_id=session_id,
                state_snapshot=state_snapshot,
                description=body.get("description", ""),
                metadata=body.get("metadata"),
                is_auto=body.get("is_auto", False),
                parent_checkpoint_id=body.get("parent_checkpoint_id")
            )
            
            return {"status": 201, "data": checkpoint.to_dict()}
        
        elif method == "GET":
            if not path_parts:
                return {"error": "缺少检查点ID", "status": 400}
            
            checkpoint_id = path_parts[0]
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
            
            if not checkpoint:
                return {"error": "检查点不存在", "status": 404}
            
            return {"status": 200, "data": checkpoint.to_dict()}
        
        else:
            return {"error": f"不支持的 HTTP 方法: {method}", "status": 405}
    
    def _handle_recover(self, method: str, path_parts: list, body: Optional[Dict]) -> Dict[str, Any]:
        """处理恢复请求"""
        if method != "POST":
            return {"error": f"不支持的 HTTP 方法: {method}", "status": 405}
        
        if not path_parts:
            return {"error": "缺少任务ID", "status": 400}
        
        task_id = path_parts[0]
        
        # 构建恢复配置
        config = RecoveryConfig()
        
        if body:
            if "strategy" in body:
                try:
                    config.strategy = RecoveryStrategy(body["strategy"])
                except ValueError:
                    return {"error": f"无效的恢复策略: {body['strategy']}", "status": 400}
            
            if "max_retries" in body:
                config.max_retries = body["max_retries"]
            
            if "checkpoint_id" in body:
                config.checkpoint_id = body["checkpoint_id"]
        
        # 执行恢复
        result = self.recovery_manager.recover_task(task_id, config)
        
        return {
            "status": 200 if result.success else 400,
            "data": {
                "success": result.success,
                "strategy_used": result.strategy_used.value,
                "checkpoint_id": result.checkpoint_id,
                "state_snapshot": result.state_snapshot,
                "error": result.error,
                "retry_count": result.retry_count,
                "recovery_time": result.recovery_time
            }
        }
    
    def _handle_statistics(self, method: str) -> Dict[str, Any]:
        """处理统计信息请求"""
        if method != "GET":
            return {"error": f"不支持的 HTTP 方法: {method}", "status": 405}
        
        stats = {
            "state_manager": self.state_manager.get_statistics(),
            "checkpoint_manager": self.checkpoint_manager.get_statistics(),
            "recovery_manager": self.recovery_manager.get_statistics()
        }
        
        return {"status": 200, "data": stats}
    
    def register_routes(self, handler_class):
        """
        注册路由到 HTTP 处理器
        
        Args:
            handler_class: HTTP 处理器类
        """
        api = self
        
        original_do_GET = handler_class.do_GET
        original_do_POST = handler_class.do_POST
        original_do_PUT = getattr(handler_class, 'do_PUT', None)
        
        def do_GET(self):
            if self.path.startswith("/api/state/"):
                body = None
                result = api.handle_request(self, "GET", self.path, body)
                self.send_response(result.get("status", 200))
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result.get("data", result), ensure_ascii=False).encode('utf-8'))
            else:
                original_do_GET(self)
        
        def do_POST(self):
            if self.path.startswith("/api/state/"):
                content_length = int(self.headers.get('Content-Length', 0))
                body = None
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    body = json.loads(post_data.decode('utf-8'))
                
                result = api.handle_request(self, "POST", self.path, body)
                self.send_response(result.get("status", 200))
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result.get("data", result), ensure_ascii=False).encode('utf-8'))
            else:
                original_do_POST(self)
        
        def do_PUT(self):
            if self.path.startswith("/api/state/"):
                content_length = int(self.headers.get('Content-Length', 0))
                body = None
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    body = json.loads(post_data.decode('utf-8'))
                
                result = api.handle_request(self, "PUT", self.path, body)
                self.send_response(result.get("status", 200))
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result.get("data", result), ensure_ascii=False).encode('utf-8'))
            elif original_do_PUT:
                original_do_PUT(self)
            else:
                self.send_response(405)
                self.end_headers()
        
        handler_class.do_GET = do_GET
        handler_class.do_POST = do_POST
        handler_class.do_PUT = do_PUT
        
        return handler_class
