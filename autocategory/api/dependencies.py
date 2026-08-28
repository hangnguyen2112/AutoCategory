"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import logging
import threading
import time

from database import SessionLocal, get_db
from models import User, APIKey
from auth import verify_token, Role, require_role, require_permission, Permission

logger = logging.getLogger(__name__)
_API_KEY_USAGE_FLUSH_SECONDS = 60.0
_api_key_usage_lock = threading.Lock()
_api_key_usage_pending: dict[int, int] = {}
_api_key_usage_last_flush: dict[int, float] = {}


def _take_api_key_usage_batch(api_key_id: int) -> int:
    """Batch hot-row usage updates while keeping counters mostly current."""
    now = time.monotonic()
    with _api_key_usage_lock:
        pending = _api_key_usage_pending.get(api_key_id, 0) + 1
        last_flush = _api_key_usage_last_flush.get(api_key_id, 0.0)
        if now - last_flush < _API_KEY_USAGE_FLUSH_SECONDS:
            _api_key_usage_pending[api_key_id] = pending
            return 0
        _api_key_usage_pending[api_key_id] = 0
        _api_key_usage_last_flush[api_key_id] = now
        return pending


def _restore_api_key_usage_batch(api_key_id: int, count: int) -> None:
    with _api_key_usage_lock:
        _api_key_usage_pending[api_key_id] = _api_key_usage_pending.get(api_key_id, 0) + count

# Security scheme
security = HTTPBearer()


def get_current_user(
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
    
    # last_login_at is updated by the login endpoint only. Detach the user and
    # end this read transaction so authenticated requests do not hold a DB
    # connection while their handlers await DeepSeek or other services.
    db.expunge(user)
    db.rollback()
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


def verify_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> Optional[APIKey]:
    """
    Verify API key from X-API-Key header
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        API key object if valid, None if no key provided
        
    Raises:
        HTTPException: 401 if API key is invalid
    """
    if x_api_key is None:
        return None
    
    # Hash the API key for lookup
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    # Authentication must finish before a StreamingResponse starts. Use a
    # short-lived session here instead of a yield dependency whose cleanup time
    # depends on the FastAPI version and response type.
    with SessionLocal() as db:
        api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        if not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive or revoked"
            )

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )

        api_key_id = api_key.id
        usage_batch = _take_api_key_usage_batch(api_key_id)
        if usage_batch:
            try:
                db.query(APIKey).filter(APIKey.id == api_key_id).update(
                    {
                        APIKey.total_requests: func.coalesce(APIKey.total_requests, 0) + usage_batch,
                        APIKey.last_used_at: datetime.utcnow(),
                    },
                    synchronize_session=False,
                )
                db.commit()
                db.refresh(api_key)
            except Exception:
                db.rollback()
                _restore_api_key_usage_batch(api_key_id, usage_batch)
                logger.exception("Could not flush API key usage for id=%s", api_key_id)
                db.refresh(api_key)
        db.expunge(api_key)
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
