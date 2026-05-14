"""
Authentication module
"""
from .password import hash_password, verify_password
from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    get_token_expiration,
)
from .permissions import (
    Role,
    Permission,
    has_permission,
    require_permission,
    require_role,
    is_admin,
    is_developer_or_admin,
)

__all__ = [
    # Password
    "hash_password",
    "verify_password",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "get_token_expiration",
    # Permissions
    "Role",
    "Permission",
    "has_permission",
    "require_permission",
    "require_role",
    "is_admin",
    "is_developer_or_admin",
]
