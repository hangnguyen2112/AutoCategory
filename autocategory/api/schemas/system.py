"""
System control schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class ServiceStatus(BaseModel):
    name: str
    status: str  # running, stopped, error, unknown
    uptime: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    error_message: Optional[str] = None


class SystemHealthResponse(BaseModel):
    overall_status: str  # healthy, degraded, unhealthy
    services: list[ServiceStatus]
    timestamp: datetime
    
    
class ServiceControlRequest(BaseModel):
    action: str  # start, stop, restart
    force: bool = False


class ServiceControlResponse(BaseModel):
    success: bool
    service_name: str
    action: str
    message: str
    new_status: Optional[str] = None


class CacheClearRequest(BaseModel):
    cache_type: str  # all, rate_limit, sessions, embeddings
    pattern: Optional[str] = None


class CacheClearResponse(BaseModel):
    success: bool
    cache_type: str
    keys_deleted: int
    message: str


class SystemLogsRequest(BaseModel):
    service: Optional[str] = None  # api, llm, qdrant, postgres, redis
    level: Optional[str] = None  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    limit: int = 100
    since: Optional[datetime] = None


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    service: str
    message: str
    details: Optional[Dict[str, Any]] = None


class SystemLogsResponse(BaseModel):
    logs: list[LogEntry]
    total: int
    filtered: int


class SystemMetricsResponse(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    timestamp: datetime


class DatabaseStatsResponse(BaseModel):
    total_users: int
    total_api_keys: int
    total_request_logs: int
    total_training_data: int
    database_size_mb: float
    oldest_log_date: Optional[datetime] = None
    newest_log_date: Optional[datetime] = None
