"""
Pydantic schemas
"""
from .auth import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserChangePassword,
    UserResponse,
    Token,
    TokenData,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    APIKeyBase,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreateResponse,
    MessageResponse,
)
from .request_log import (
    RequestLogResponse,
    RequestLogFilter,
    RequestLogStats,
)
from .training_data import (
    TrainingDataCreate,
    TrainingDataUpdate,
    TrainingDataResponse,
    TrainingDataStats,
)
from .system_config import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    SystemConfigBulkUpdate,
)
from .category_sync import (
    CategorySyncResponse,
    CategorySyncStats,
    CategoryImportRequest,
    CategoryImportResponse,
    CategoryRebuildIndexRequest,
    CategoryRebuildIndexResponse,
)
from .system import (
    ServiceStatus,
    SystemHealthResponse,
    ServiceControlRequest,
    ServiceControlResponse,
    CacheClearRequest,
    CacheClearResponse,
    SystemLogsRequest,
    SystemLogsResponse,
    SystemMetricsResponse,
    DatabaseStatsResponse,
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserChangePassword",
    "UserResponse",
    # Auth
    "Token",
    "TokenData",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    # API Key
    "APIKeyBase",
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyCreateResponse",
    # Generic
    "MessageResponse",
    # Request Log
    "RequestLogResponse",
    "RequestLogFilter",
    "RequestLogStats",
    # Training Data
    "TrainingDataCreate",
    "TrainingDataUpdate",
    "TrainingDataResponse",
    "TrainingDataStats",
    # System Config
    "SystemConfigCreate",
    "SystemConfigUpdate",
    "SystemConfigResponse",
    "SystemConfigBulkUpdate",
    # Category Sync
    "CategorySyncResponse",
    "CategorySyncStats",
    "CategoryImportRequest",
    "CategoryImportResponse",
    "CategoryRebuildIndexRequest",
    "CategoryRebuildIndexResponse",
    # System
    "ServiceStatus",
    "SystemHealthResponse",
    "ServiceControlRequest",
    "ServiceControlResponse",
    "CacheClearRequest",
    "CacheClearResponse",
    "SystemLogsRequest",
    "SystemLogsResponse",
    "SystemMetricsResponse",
    "DatabaseStatsResponse",
]
