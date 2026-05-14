"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib

from database import get_db
from models import User, APIKey
from auth import verify_token, Role, require_role, require_permission, Permission

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current user if active
        
    Raises:
        HTTPException: 403 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user and verify admin role
    
    Args:
        current_user: Current user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    require_role(current_user.role, [Role.ADMIN])
    return current_user


async def get_current_developer_or_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user and verify developer or admin role
    
    Args:
        current_user: Current user
        
    Returns:
        Current user if developer or admin
        
    Raises:
        HTTPException: 403 if user is not developer or admin
    """
    require_role(current_user.role, [Role.ADMIN, Role.DEVELOPER])
    return current_user


async def verify_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
    db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    Verify API key from X-API-Key header
    
    Args:
        x_api_key: API key from X-API-Key header
        db: Database session
        
    Returns:
        API key object if valid, None if no key provided
        
    Raises:
        HTTPException: 401 if API key is invalid
    """
    if x_api_key is None:
        return None
    
    # Hash the API key for lookup
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    # Look up API key in database
    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
    
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if key is active
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive or revoked"
        )
    
    # Check if key has expired
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
    
    # Update usage stats
    api_key.total_requests += 1
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    return api_key


async def require_api_key(
    api_key: Optional[APIKey] = Depends(verify_api_key)
) -> APIKey:
    """
    Require valid API key
    
    Args:
        api_key: API key from verify_api_key
        
    Returns:
        API key object
        
    Raises:
        HTTPException: 401 if no API key provided
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    return api_key


async def get_api_key_with_permission(
    permission: Permission,
    api_key: APIKey = Depends(require_api_key)
) -> APIKey:
    """
    Get API key and verify it has required permission
    
    Args:
        permission: Required permission
        api_key: API key from require_api_key
        
    Returns:
        API key object
        
    Raises:
        HTTPException: 403 if API key doesn't have permission
    """
    if permission == Permission.CLASSIFY and not api_key.can_classify:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have classify permission"
        )
    
    if permission == Permission.GENERATE and not api_key.can_generate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have generate permission"
        )
    
    if permission in [Permission.SYSTEM_CONTROL, Permission.SYSTEM_CONFIG] and not api_key.can_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have admin permission"
        )
    
    return api_key


# Type aliases for cleaner code
CurrentUser = Annotated[User, Depends(get_current_active_user)]
CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
CurrentDeveloperOrAdminUser = Annotated[User, Depends(get_current_developer_or_admin_user)]
ValidAPIKey = Annotated[APIKey, Depends(require_api_key)]
