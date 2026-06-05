"""
API 注册中心

统一管理所有模块的 API 路由器注册到主系统。
解决模块 API 未集成到主系统的问题。

使用方式:
    from api_registry import APIRegistry
    
    app = FastAPI()
    registry = APIRegistry(app)
    
    # 注册模块
    registry.register_module("code_executor", executor_router, prefix="/api/executor")
"""

from fastapi import FastAPI, APIRouter
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class APIRegistry:
    """API 注册中心
    
    统一管理所有模块的 API 路由器注册到主系统。
    """
    
    def __init__(self, app: FastAPI):
        """初始化 API 注册中心
        
        Args:
            app: FastAPI 应用实例
        """
        self.app = app
        self.registered_routers: Dict[str, APIRouter] = {}
        self.registration_order: List[str] = []
        self.module_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_module(
        self, 
        module_name: str, 
        router: APIRouter, 
        prefix: str = "", 
        tags: List[str] = None,
        description: str = ""
    ) -> bool:
        """注册模块 API 路由器
        
        Args:
            module_name: 模块名称
            router: APIRouter 实例
            prefix: URL 前缀
            tags: API 标签
            description: 模块描述
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 检查是否已注册
            if module_name in self.registered_routers:
                logger.warning(f"⚠️ 模块 {module_name} 已注册，将覆盖")
            
            # 注册路由
            self.app.include_router(
                router,
                prefix=prefix,
                tags=tags or [module_name]
            )
            
            # 记录注册信息
            self.registered_routers[module_name] = router
            self.module_metadata[module_name] = {
                "prefix": prefix,
                "tags": tags or [module_name],
                "description": description
            }
            
            if module_name not in self.registration_order:
                self.registration_order.append(module_name)
            
            logger.info(f"✅ 已注册模块: {module_name} (prefix: {prefix})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 注册模块 {module_name} 失败: {e}")
            return False
    
    def unregister_module(self, module_name: str) -> bool:
        """注销模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if module_name in self.registered_routers:
                del self.registered_routers[module_name]
                del self.module_metadata[module_name]
                if module_name in self.registration_order:
                    self.registration_order.remove(module_name)
                logger.info(f"✅ 已注销模块: {module_name}")
                return True
            else:
                logger.warning(f"⚠️ 模块 {module_name} 未注册")
                return False
        except Exception as e:
            logger.error(f"❌ 注销模块 {module_name} 失败: {e}")
            return False
    
    def get_registered_modules(self) -> List[str]:
        """获取已注册的模块列表
        
        Returns:
            List[str]: 已注册的模块名称列表
        """
        return self.registration_order.copy()
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息
        
        Returns:
            Dict[str, Any]: 模块信息字典
        """
        return {
            "total_modules": len(self.registered_routers),
            "modules": list(self.registered_routers.keys()),
            "registration_order": self.registration_order,
            "metadata": self.module_metadata
        }
    
    def is_module_registered(self, module_name: str) -> bool:
        """检查模块是否已注册
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否已注册
        """
        return module_name in self.registered_routers
    
    def get_module_routes(self, module_name: str) -> List[str]:
        """获取模块的路由列表
        
        Args:
            module_name: 模块名称
            
        Returns:
            List[str]: 路由列表
        """
        if module_name not in self.registered_routers:
            return []
        
        router = self.registered_routers[module_name]
        routes = []
        
        for route in router.routes:
            if hasattr(route, "path"):
                routes.append(route.path)
        
        return routes
    
    def get_all_routes(self) -> Dict[str, List[str]]:
        """获取所有模块的路由
        
        Returns:
            Dict[str, List[str]]: 模块路由字典
        """
        all_routes = {}
        
        for module_name in self.registration_order:
            all_routes[module_name] = self.get_module_routes(module_name)
        
        return all_routes
    
    def print_registration_summary(self):
        """打印注册摘要"""
        print("\n" + "=" * 60)
        print("API 注册摘要")
        print("=" * 60)
        print(f"已注册模块数量: {len(self.registered_routers)}")
        print("\n模块列表:")
        
        for i, module_name in enumerate(self.registration_order, 1):
            metadata = self.module_metadata.get(module_name, {})
            prefix = metadata.get("prefix", "N/A")
            description = metadata.get("description", "")
            
            print(f"  {i}. {module_name}")
            print(f"     前缀: {prefix}")
            if description:
                print(f"     描述: {description}")
        
        print("=" * 60 + "\n")


def create_health_router(registry: APIRegistry) -> APIRouter:
    """创建健康检查路由
    
    Args:
        registry: API 注册中心实例
        
    Returns:
        APIRouter: 健康检查路由器
    """
    router = APIRouter(tags=["system"])
    
    @router.get("/api/health")
    async def health_check():
        """系统健康检查"""
        return {
            "status": "healthy",
            "modules": registry.get_registered_modules(),
            "module_count": len(registry.get_registered_modules())
        }
    
    @router.get("/api/modules")
    async def get_modules():
        """获取所有已注册模块信息"""
        return registry.get_module_info()
    
    @router.get("/api/modules/{module_name}")
    async def get_module_detail(module_name: str):
        """获取指定模块详细信息"""
        if not registry.is_module_registered(module_name):
            return {"error": f"模块 {module_name} 未注册"}, 404
        
        return {
            "name": module_name,
            "metadata": registry.module_metadata.get(module_name, {}),
            "routes": registry.get_module_routes(module_name)
        }
    
    return router


# 示例用法
if __name__ == "__main__":
    # 测试 APIRegistry
    from fastapi import FastAPI
    
    app = FastAPI()
    registry = APIRegistry(app)
    
    # 创建测试路由
    test_router = APIRouter(prefix="/api/test", tags=["test"])
    
    @test_router.get("/hello")
    async def hello():
        return {"message": "Hello from test module"}
    
    # 注册模块
    registry.register_module("test_module", test_router, prefix="/api/test", description="测试模块")
    
    # 打印摘要
    registry.print_registration_summary()
    
    # 获取模块信息
    print(registry.get_module_info())
