"""
Role-Based Access Control (RBAC) and permissions
"""
from enum import Enum
from typing import List
from fastapi import HTTPException, status


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class Permission(str, Enum):
    """System permissions"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # API key management
    API_KEY_CREATE = "api_key:create"
    API_KEY_READ = "api_key:read"
    API_KEY_REVOKE = "api_key:revoke"
    
    # System control
    SYSTEM_CONTROL = "system:control"
    SYSTEM_CONFIG = "system:config"
    
    # Data management
    DATA_IMPORT = "data:import"
    DATA_EXPORT = "data:export"
    
    # Training
    TRAINING_START = "training:start"
    TRAINING_VIEW = "training:view"
    TRAINING_DEPLOY = "training:deploy"
    
    # Monitoring
    MONITORING_VIEW = "monitoring:view"
    LOGS_VIEW = "logs:view"
    
    # Classification & generation (API usage)
    CLASSIFY = "classify"
    GENERATE = "generate"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.ADMIN: [
        # Admins have all permissions
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_READ,
        Permission.API_KEY_REVOKE,
        Permission.SYSTEM_CONTROL,
        Permission.SYSTEM_CONFIG,
        Permission.DATA_IMPORT,
        Permission.DATA_EXPORT,
        Permission.TRAINING_START,
        Permission.TRAINING_VIEW,
        Permission.TRAINING_DEPLOY,
        Permission.MONITORING_VIEW,
        Permission.LOGS_VIEW,
        Permission.CLASSIFY,
        Permission.GENERATE,
    ],
    Role.DEVELOPER: [
        # Developers can manage their own API keys, view data, use APIs
        Permission.USER_READ,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_READ,
        Permission.DATA_EXPORT,
        Permission.TRAINING_VIEW,
        Permission.MONITORING_VIEW,
        Permission.LOGS_VIEW,
        Permission.CLASSIFY,
        Permission.GENERATE,
    ],
    Role.VIEWER: [
        # Viewers can only view data
        Permission.USER_READ,
        Permission.MONITORING_VIEW,
        Permission.LOGS_VIEW,
    ],
}


def has_permission(user_role: str, permission: Permission) -> bool:
    """
    Check if a user role has a specific permission
    
    Args:
        user_role: User's role (admin, developer, viewer)
        permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    try:
        role = Role(user_role)
        return permission in ROLE_PERMISSIONS.get(role, [])
    except ValueError:
        return False


def require_permission(user_role: str, permission: Permission):
    """
    Raise HTTPException if user doesn't have required permission
    
    Args:
        user_role: User's role
        permission: Required permission
        
    Raises:
        HTTPException: 403 Forbidden if user doesn't have permission
    """
    if not has_permission(user_role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {permission.value}"
        )


def require_role(user_role: str, required_roles: List[Role]):
    """
    Raise HTTPException if user doesn't have one of the required roles
    
    Args:
        user_role: User's role
        required_roles: List of acceptable roles
        
    Raises:
        HTTPException: 403 Forbidden if user doesn't have required role
    """
    try:
        role = Role(user_role)
        if role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {[r.value for r in required_roles]}"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user role"
        )


def is_admin(user_role: str) -> bool:
    """Check if user is admin"""
    return user_role == Role.ADMIN.value


def is_developer_or_admin(user_role: str) -> bool:
    """Check if user is developer or admin"""
    return user_role in [Role.ADMIN.value, Role.DEVELOPER.value]
