"""
System control and monitoring endpoints (Admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import psutil
import redis as redis_lib

from database import get_db
from models import User, APIKey, RequestLog, TrainingData
from schemas.system import (
    SystemHealthResponse,
    ServiceStatus,
    ServiceControlRequest,
    ServiceControlResponse,
    CacheClearRequest,
    CacheClearResponse,
    SystemLogsRequest,
    SystemLogsResponse,
    LogEntry,
    SystemMetricsResponse,
    DatabaseStatsResponse,
)
from dependencies import CurrentAdminUser
from config import settings

router = APIRouter(prefix="/api/admin/system", tags=["Admin - System"])


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get overall system health status
    """
    services = []
    
    # Check API (always running if we're here)
    services.append(ServiceStatus(
        name="api",
        status="healthy",
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_mb=psutil.Process().memory_info().rss / 1024 / 1024
    ))
    
    # Check PostgreSQL
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        services.append(ServiceStatus(
            name="postgres",
            status="healthy",
            cpu_percent=0.0,
            memory_mb=0.0
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="postgres",
            status="unhealthy",
            cpu_percent=0.0,
            memory_mb=0.0,
            error_message=str(e)
        ))
    
    # Check Redis
    try:
        redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        services.append(ServiceStatus(
            name="redis",
            status="healthy",
            cpu_percent=0.0,
            memory_mb=0.0
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="redis",
            status="unhealthy",
            cpu_percent=0.0,
            memory_mb=0.0,
            error_message=str(e)
        ))
    
    # Check Qdrant
    try:
        from services.qdrant_service import QdrantService
        qdrant = QdrantService()
        collections = qdrant.client.get_collections()
        services.append(ServiceStatus(
            name="qdrant",
            status="healthy",
            cpu_percent=0.0,
            memory_mb=0.0
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="qdrant",
            status="unhealthy",
            cpu_percent=0.0,
            memory_mb=0.0,
            error_message=str(e)
        ))
    
    # Check LLM Server
    try:
        import httpx
        response = httpx.get(f"{settings.llama_base_url}/health", timeout=5)
        if response.status_code == 200:
            services.append(ServiceStatus(
                name="llm",
                status="healthy",
                cpu_percent=0.0,
                memory_mb=0.0
            ))
        else:
            services.append(ServiceStatus(
                name="llm",
                status="unhealthy",
                cpu_percent=0.0,
                memory_mb=0.0,
                error_message=f"HTTP {response.status_code}"
            ))
    except Exception as e:
        services.append(ServiceStatus(
            name="llm",
            status="unhealthy",
            cpu_percent=0.0,
            memory_mb=0.0,
            error_message=str(e)
        ))
    
    # Determine overall status
    error_count = sum(1 for s in services if s.status != "healthy")
    if error_count == 0:
        overall_status = "healthy"
    elif error_count <= 2:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return SystemHealthResponse(
        overall_status=overall_status,
        services=services,
        timestamp=datetime.utcnow()
    )


@router.post("/services/{service_name}/control", response_model=ServiceControlResponse)
async def control_service(
    service_name: str,
    request: ServiceControlRequest,
    current_admin: CurrentAdminUser
):
    """
    Control service (start/stop/restart)
    
    Note: This endpoint provides commands but requires Docker access
    to actually control services. In production, this should use
    Docker API or orchestration system.
    """
    allowed_services = ["api", "llm", "qdrant", "postgres", "redis"]
    
    if service_name not in allowed_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service '{service_name}' not controllable. Allowed: {allowed_services}"
        )
    
    # In production, this would call Docker API or K8s API
    # For now, return the command that should be run
    
    if request.action == "restart":
        command = f"docker-compose restart {service_name}"
    elif request.action == "stop":
        command = f"docker-compose stop {service_name}"
    elif request.action == "start":
        command = f"docker-compose start {service_name}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {request.action}"
        )
    
    return ServiceControlResponse(
        success=False,  # Not actually executed
        service_name=service_name,
        action=request.action,
        message=f"Manual execution required: {command}",
        new_status="unknown"
    )


@router.post("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(
    request: CacheClearRequest,
    current_admin: CurrentAdminUser
):
    """
    Clear Redis cache
    """
    try:
        redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
        
        if request.cache_type == "all":
            # Flush all Redis keys
            keys_deleted = redis_client.flushdb()
            keys_deleted = "all"
        else:
            # Delete keys by pattern
            pattern = request.pattern or f"{request.cache_type}:*"
            keys = redis_client.keys(pattern)
            if keys:
                keys_deleted = redis_client.delete(*keys)
            else:
                keys_deleted = 0
        
        return CacheClearResponse(
            success=True,
            cache_type=request.cache_type,
            keys_deleted=keys_deleted if isinstance(keys_deleted, int) else 0,
            message=f"Cleared {request.cache_type} cache"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache clear failed: {str(e)}"
        )


@router.get("/logs", response_model=SystemLogsResponse)
async def get_system_logs(
    current_admin: CurrentAdminUser,
    service: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    since: Optional[datetime] = None
):
    """
    Get system logs
    
    Note: This is a simplified version. In production, integrate with
    proper logging system (ELK, Loki, etc.)
    """
    import os
    
    logs = []
    
    # Read from log file if it exists
    log_file = settings.log_file
    if log_file and os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
            # Parse last N lines
            for line in lines[-limit:]:
                # Simple parsing (adjust based on your log format)
                try:
                    # Example format: "2026-05-06 10:30:45 [INFO] api: Message"
                    parts = line.strip().split(' ', 4)
                    if len(parts) >= 5:
                        timestamp_str = f"{parts[0]} {parts[1]}"
                        log_level = parts[2].strip('[]')
                        service_name = parts[3].rstrip(':')
                        message = parts[4]
                        
                        # Filter by level
                        if level and log_level != level:
                            continue
                        
                        # Filter by service
                        if service and service_name != service:
                            continue
                        
                        log_entry = LogEntry(
                            timestamp=datetime.fromisoformat(timestamp_str),
                            level=log_level,
                            service=service_name,
                            message=message
                        )
                        
                        # Filter by time
                        if since and log_entry.timestamp < since:
                            continue
                        
                        logs.append(log_entry)
                except Exception:
                    # Skip malformed lines
                    continue
    
    return SystemLogsResponse(
        logs=logs[-limit:],
        total=len(logs),
        filtered=len(logs)
    )


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_admin: CurrentAdminUser
):
    """
    Get current system metrics (CPU, memory, disk, network)
    """
    # Network I/O
    net_io = psutil.net_io_counters()
    
    return SystemMetricsResponse(
        cpu_percent=psutil.cpu_percent(interval=0.5),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage('/').percent,
        network_sent_mb=net_io.bytes_sent / 1024 / 1024,
        network_recv_mb=net_io.bytes_recv / 1024 / 1024,
        timestamp=datetime.utcnow()
    )


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get database statistics
    """
    from sqlalchemy import func
    
    # Count records
    total_users = db.query(User).count()
    total_api_keys = db.query(APIKey).count()
    total_request_logs = db.query(RequestLog).count()
    total_training_data = db.query(TrainingData).count()
    
    # Get date range of logs
    date_range = db.query(
        func.min(RequestLog.created_at).label('oldest'),
        func.max(RequestLog.created_at).label('newest')
    ).first()
    
    # Get database size (PostgreSQL specific)
    try:
        size_query = db.execute(
            "SELECT pg_database_size(current_database())"
        )
        db_size_bytes = size_query.scalar()
        db_size_mb = db_size_bytes / 1024 / 1024 if db_size_bytes else 0
    except Exception:
        db_size_mb = 0
    
    return DatabaseStatsResponse(
        total_users=total_users,
        total_api_keys=total_api_keys,
        total_request_logs=total_request_logs,
        total_training_data=total_training_data,
        database_size_mb=round(db_size_mb, 2),
        oldest_log_date=date_range.oldest,
        newest_log_date=date_range.newest
    )


@router.get("/info")
async def get_system_info(
    current_admin: CurrentAdminUser
):
    """
    Get system information
    """
    return {
        "python_version": f"{psutil.PROCFS_PATH}",
        "cpu_count": psutil.cpu_count(),
        "total_memory_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
        "platform": psutil.WINDOWS if hasattr(psutil, 'WINDOWS') else "linux",
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }
