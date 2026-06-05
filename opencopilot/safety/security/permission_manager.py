# security_module/permission_manager.py

"""
权限管理器

负责管理用户权限，包括权限的添加、删除、检查等操作。
"""

import time
import logging
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from .models import Permission, PermissionAction, ResourceType

logger = logging.getLogger(__name__)


class PermissionManager:
    """权限管理器
    
    管理用户权限，支持：
    - 基于角色的权限控制 (RBAC)
    - 基于资源的权限控制
    - 权限继承
    - 条件权限
    """
    
    def __init__(self):
        """初始化权限管理器"""
        # 用户权限映射: user_id -> Set[permission_id]
        self._user_permissions: Dict[str, Set[str]] = defaultdict(set)
        
        # 角色权限映射: role -> Set[permission_id]
        self._role_permissions: Dict[str, Set[str]] = defaultdict(set)
        
        # 用户角色映射: user_id -> Set[role]
        self._user_roles: Dict[str, Set[str]] = defaultdict(set)
        
        # 权限存储: permission_id -> Permission
        self._permissions: Dict[str, Permission] = {}
        
        # 默认权限
        self._init_default_permissions()
    
    def _init_default_permissions(self):
        """初始化默认权限"""
        # 基本读取权限
        self.add_permission(Permission(
            permission_id="perm_read_tools",
            resource=ResourceType.TOOL.value,
            action=PermissionAction.READ.value,
            description="Read tool information"
        ))
        
        self.add_permission(Permission(
            permission_id="perm_read_files",
            resource=ResourceType.FILE.value,
            action=PermissionAction.READ.value,
            description="Read file content"
        ))
        
        # 执行权限
        self.add_permission(Permission(
            permission_id="perm_execute_tools",
            resource=ResourceType.TOOL.value,
            action=PermissionAction.EXECUTE.value,
            description="Execute tools"
        ))
        
        self.add_permission(Permission(
            permission_id="perm_execute_code",
            resource=ResourceType.CODE.value,
            action=PermissionAction.EXECUTE.value,
            description="Execute code"
        ))
        
        # 写入权限
        self.add_permission(Permission(
            permission_id="perm_write_files",
            resource=ResourceType.FILE.value,
            action=PermissionAction.WRITE.value,
            description="Write file content"
        ))
        
        # 删除权限
        self.add_permission(Permission(
            permission_id="perm_delete_files",
            resource=ResourceType.FILE.value,
            action=PermissionAction.DELETE.value,
            description="Delete files"
        ))
        
        # 管理权限
        self.add_permission(Permission(
            permission_id="perm_admin_system",
            resource=ResourceType.SYSTEM.value,
            action=PermissionAction.ADMIN.value,
            description="System administration"
        ))
        
        # 默认角色
        self._create_default_roles()
    
    def _create_default_roles(self):
        """创建默认角色"""
        # 查看者角色
        self.create_role("viewer", "Read-only access")
        self.assign_permission_to_role("perm_read_tools", "viewer")
        self.assign_permission_to_role("perm_read_files", "viewer")
        
        # 用户角色
        self.create_role("user", "Standard user access")
        self.assign_permission_to_role("perm_read_tools", "user")
        self.assign_permission_to_role("perm_read_files", "user")
        self.assign_permission_to_role("perm_execute_tools", "user")
        self.assign_permission_to_role("perm_execute_code", "user")
        self.assign_permission_to_role("perm_write_files", "user")
        
        # 管理员角色
        self.create_role("admin", "Full administrative access")
        for perm_id in self._permissions.keys():
            self.assign_permission_to_role(perm_id, "admin")
    
    def add_permission(self, permission: Permission) -> bool:
        """添加权限
        
        Args:
            permission: 权限对象
            
        Returns:
            bool: 是否添加成功
        """
        if permission.permission_id in self._permissions:
            logger.warning(f"Permission {permission.permission_id} already exists")
            return False
        
        self._permissions[permission.permission_id] = permission
        logger.info(f"Added permission: {permission.permission_id}")
        return True
    
    def remove_permission(self, permission_id: str) -> bool:
        """移除权限
        
        Args:
            permission_id: 权限 ID
            
        Returns:
            bool: 是否移除成功
        """
        if permission_id not in self._permissions:
            return False
        
        # 从所有用户和角色中移除
        for user_perms in self._user_permissions.values():
            user_perms.discard(permission_id)
        
        for role_perms in self._role_permissions.values():
            role_perms.discard(permission_id)
        
        del self._permissions[permission_id]
        logger.info(f"Removed permission: {permission_id}")
        return True
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """获取权限
        
        Args:
            permission_id: 权限 ID
            
        Returns:
            Optional[Permission]: 权限对象
        """
        return self._permissions.get(permission_id)
    
    def list_permissions(self) -> List[Permission]:
        """列出所有权限
        
        Returns:
            List[Permission]: 权限列表
        """
        return list(self._permissions.values())
    
    def create_role(self, role: str, description: str = "") -> bool:
        """创建角色
        
        Args:
            role: 角色名称
            description: 角色描述
            
        Returns:
            bool: 是否创建成功
        """
        if role in self._role_permissions:
            logger.warning(f"Role {role} already exists")
            return False
        
        self._role_permissions[role] = set()
        logger.info(f"Created role: {role}")
        return True
    
    def delete_role(self, role: str) -> bool:
        """删除角色
        
        Args:
            role: 角色名称
            
        Returns:
            bool: 是否删除成功
        """
        if role not in self._role_permissions:
            return False
        
        # 从所有用户中移除角色
        for user_roles in self._user_roles.values():
            user_roles.discard(role)
        
        del self._role_permissions[role]
        logger.info(f"Deleted role: {role}")
        return True
    
    def assign_permission_to_role(self, permission_id: str, role: str) -> bool:
        """将权限分配给角色
        
        Args:
            permission_id: 权限 ID
            role: 角色名称
            
        Returns:
            bool: 是否分配成功
        """
        if permission_id not in self._permissions:
            logger.warning(f"Permission {permission_id} not found")
            return False
        
        if role not in self._role_permissions:
            logger.warning(f"Role {role} not found")
            return False
        
        self._role_permissions[role].add(permission_id)
        logger.info(f"Assigned permission {permission_id} to role {role}")
        return True
    
    def remove_permission_from_role(self, permission_id: str, role: str) -> bool:
        """从角色中移除权限
        
        Args:
            permission_id: 权限 ID
            role: 角色名称
            
        Returns:
            bool: 是否移除成功
        """
        if role not in self._role_permissions:
            return False
        
        self._role_permissions[role].discard(permission_id)
        logger.info(f"Removed permission {permission_id} from role {role}")
        return True
    
    def assign_role_to_user(self, user_id: str, role: str) -> bool:
        """将角色分配给用户
        
        Args:
            user_id: 用户 ID
            role: 角色名称
            
        Returns:
            bool: 是否分配成功
        """
        if role not in self._role_permissions:
            logger.warning(f"Role {role} not found")
            return False
        
        self._user_roles[user_id].add(role)
        logger.info(f"Assigned role {role} to user {user_id}")
        return True
    
    def remove_role_from_user(self, user_id: str, role: str) -> bool:
        """从用户中移除角色
        
        Args:
            user_id: 用户 ID
            role: 角色名称
            
        Returns:
            bool: 是否移除成功
        """
        if user_id not in self._user_roles:
            return False
        
        self._user_roles[user_id].discard(role)
        logger.info(f"Removed role {role} from user {user_id}")
        return True
    
    def assign_permission_to_user(self, permission_id: str, user_id: str) -> bool:
        """将权限直接分配给用户
        
        Args:
            permission_id: 权限 ID
            user_id: 用户 ID
            
        Returns:
            bool: 是否分配成功
        """
        if permission_id not in self._permissions:
            logger.warning(f"Permission {permission_id} not found")
            return False
        
        self._user_permissions[user_id].add(permission_id)
        logger.info(f"Assigned permission {permission_id} to user {user_id}")
        return True
    
    def remove_permission_from_user(self, permission_id: str, user_id: str) -> bool:
        """从用户中移除权限
        
        Args:
            permission_id: 权限 ID
            user_id: 用户 ID
            
        Returns:
            bool: 是否移除成功
        """
        if user_id not in self._user_permissions:
            return False
        
        self._user_permissions[user_id].discard(permission_id)
        logger.info(f"Removed permission {permission_id} from user {user_id}")
        return True
    
    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """检查用户是否有权限
        
        Args:
            user_id: 用户 ID
            resource: 资源类型
            action: 动作类型
            context: 上下文信息
            
        Returns:
            bool: 是否有权限
        """
        # 获取用户的所有权限
        user_perms = self._get_user_permissions(user_id)
        
        # 检查是否有匹配的权限
        for perm_id in user_perms:
            perm = self._permissions.get(perm_id)
            if not perm:
                continue
            
            # 检查权限是否过期
            if perm.is_expired():
                continue
            
            # 检查资源和动作是否匹配
            if self._match_permission(perm, resource, action, context):
                return True
        
        return False
    
    def _get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户的所有权限
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Set[str]: 权限 ID 集合
        """
        perms = set()
        
        # 直接分配的权限
        if user_id in self._user_permissions:
            perms.update(self._user_permissions[user_id])
        
        # 通过角色继承的权限
        if user_id in self._user_roles:
            for role in self._user_roles[user_id]:
                if role in self._role_permissions:
                    perms.update(self._role_permissions[role])
        
        return perms
    
    def _match_permission(
        self,
        permission: Permission,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """检查权限是否匹配
        
        Args:
            permission: 权限对象
            resource: 资源类型
            action: 动作类型
            context: 上下文信息
            
        Returns:
            bool: 是否匹配
        """
        # 检查资源匹配
        if permission.resource != "*" and permission.resource != resource:
            return False
        
        # 检查动作匹配
        if permission.action != "*" and permission.action != action:
            return False
        
        # 检查条件
        if permission.conditions and context:
            for key, value in permission.conditions.items():
                if key not in context or context[key] != value:
                    return False
        
        return True
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """获取用户的角色
        
        Args:
            user_id: 用户 ID
            
        Returns:
            List[str]: 角色列表
        """
        return list(self._user_roles.get(user_id, set()))
    
    def get_role_permissions(self, role: str) -> List[Permission]:
        """获取角色的权限
        
        Args:
            role: 角色名称
            
        Returns:
            List[Permission]: 权限列表
        """
        if role not in self._role_permissions:
            return []
        
        return [
            self._permissions[perm_id]
            for perm_id in self._role_permissions[role]
            if perm_id in self._permissions
        ]
    
    def get_user_permissions_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户权限摘要
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Dict[str, Any]: 权限摘要
        """
        roles = self.get_user_roles(user_id)
        direct_perms = list(self._user_permissions.get(user_id, set()))
        all_perms = list(self._get_user_permissions(user_id))
        
        return {
            "user_id": user_id,
            "roles": roles,
            "direct_permissions": direct_perms,
            "all_permissions": all_perms,
            "permission_count": len(all_perms)
        }
