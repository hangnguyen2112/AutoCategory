"""
Request log management endpoints (Admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta

from database import get_db
from models import RequestLog, User, APIKey
from schemas.request_log import (
    RequestLogResponse,
    RequestLogFilter,
    RequestLogStats,
    RequestLogListResponse,
)
from dependencies import CurrentAdminUser

router = APIRouter(prefix="/api/admin/logs", tags=["Admin - Logs"])


@router.get("/requests", response_model=RequestLogListResponse)
async def list_request_logs(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    status_group: Optional[str] = Query(None, pattern="^(2xx|4xx|5xx)$"),
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    user_id: Optional[int] = None,
    api_key_id: Optional[int] = None,
    has_error: Optional[bool] = None,
    was_corrected: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    List request logs with filtering
    """
    query = db.query(RequestLog)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            RequestLog.endpoint.ilike(search_pattern)
            | RequestLog.input_title.ilike(search_pattern)
        )

    if status_group:
        if status_group == "2xx":
            query = query.filter(
                RequestLog.response_status >= 200,
                RequestLog.response_status < 300,
            )
        elif status_group == "4xx":
            query = query.filter(
                RequestLog.response_status >= 400,
                RequestLog.response_status < 500,
            )
        elif status_group == "5xx":
            query = query.filter(RequestLog.response_status >= 500)
    
    # Apply filters
    if endpoint:
        query = query.filter(RequestLog.endpoint.ilike(f"%{endpoint}%"))
    
    if method:
        query = query.filter(RequestLog.method == method.upper())
    
    if status_code:
        query = query.filter(RequestLog.response_status == status_code)
    
    if user_id:
        query = query.filter(RequestLog.user_id == user_id)
    
    if api_key_id:
        query = query.filter(RequestLog.api_key_id == api_key_id)
    
    if has_error is not None:
        if has_error:
            query = query.filter(RequestLog.error_message.isnot(None))
        else:
            query = query.filter(RequestLog.error_message.is_(None))
    
    if was_corrected is not None:
        query = query.filter(RequestLog.was_corrected == was_corrected)
    
    if start_date:
        query = query.filter(RequestLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(RequestLog.created_at <= end_date)
    
    total = query.count()

    # Order by created_at descending (newest first)
    query = query.order_by(desc(RequestLog.created_at))

    # Paginate
    logs = query.offset(skip).limit(limit).all()

    page = (skip // limit) + 1
    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return RequestLogListResponse(
        items=[RequestLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/requests/{log_id}", response_model=RequestLogResponse)
async def get_request_log(
    log_id: int,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get request log by ID
    """
    log = db.query(RequestLog).filter(RequestLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request log not found"
        )
    
    return RequestLogResponse.model_validate(log)


@router.get("/stats", response_model=RequestLogStats)
async def get_request_stats(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get request statistics
    """
    # Default to last 24 hours if no dates provided
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=1)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Base query
    query = db.query(RequestLog).filter(
        RequestLog.created_at >= start_date,
        RequestLog.created_at <= end_date
    )
    
    # Total requests
    total_requests = query.count()
    
    # Success rate (2xx status codes)
    success_count = query.filter(
        RequestLog.response_status >= 200,
        RequestLog.response_status < 300
    ).count()
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
    
    # Average response time
    avg_response_time_result = query.with_entities(
        func.avg(RequestLog.response_time_ms)
    ).scalar()
    avg_response_time = float(avg_response_time_result) if avg_response_time_result else 0
    
    # Error count
    error_count = query.filter(RequestLog.error_message.isnot(None)).count()
    
    # Correction rate
    total_classifications = query.filter(
        RequestLog.predicted_category_id.isnot(None)
    ).count()
    corrections = query.filter(RequestLog.was_corrected == True).count()
    correction_rate = (corrections / total_classifications * 100) if total_classifications > 0 else 0
    
    # Requests by endpoint
    endpoint_stats = db.query(
        RequestLog.endpoint,
        func.count(RequestLog.id).label('count')
    ).filter(
        RequestLog.created_at >= start_date,
        RequestLog.created_at <= end_date
    ).group_by(RequestLog.endpoint).all()
    
    requests_by_endpoint = {ep: count for ep, count in endpoint_stats}
    
    # Requests by status code
    status_stats = db.query(
        RequestLog.response_status,
        func.count(RequestLog.id).label('count')
    ).filter(
        RequestLog.created_at >= start_date,
        RequestLog.created_at <= end_date
    ).group_by(RequestLog.response_status).all()
    
    requests_by_status = {str(status): count for status, count in status_stats if status}
    
    # Top categories
    category_stats = db.query(
        RequestLog.predicted_category_name,
        func.count(RequestLog.id).label('count')
    ).filter(
        RequestLog.created_at >= start_date,
        RequestLog.created_at <= end_date,
        RequestLog.predicted_category_name.isnot(None)
    ).group_by(RequestLog.predicted_category_name).order_by(desc('count')).limit(10).all()
    
    top_categories = [{"name": name, "count": count} for name, count in category_stats]
    
    # Top LLM reasons (from rerank step)
    reason_stats = db.query(
        RequestLog.llm_reason,
        RequestLog.decision,
        func.count(RequestLog.id).label('count')
    ).filter(
        RequestLog.created_at >= start_date,
        RequestLog.created_at <= end_date,
        RequestLog.llm_reason.isnot(None),
        RequestLog.llm_reason != ''
    ).group_by(RequestLog.llm_reason, RequestLog.decision).order_by(desc('count')).limit(10).all()
    
    top_reasons = [{"reason": reason, "decision": decision, "count": count} for reason, decision, count in reason_stats]
    
    return RequestLogStats(
        total_requests=total_requests,
        success_rate=round(success_rate, 2),
        avg_response_time=round(avg_response_time, 2),
        error_count=error_count,
        correction_rate=round(correction_rate, 2),
        requests_by_endpoint=requests_by_endpoint,
        requests_by_status=requests_by_status,
        top_categories=top_categories,
        top_reasons=top_reasons
    )


@router.delete("/requests/cleanup")
async def cleanup_old_logs(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    days_to_keep: int = Query(0, ge=0, le=365)
):
    """
    Delete request logs. When days_to_keep=0 (default), deletes ALL logs.
    When days_to_keep>0, deletes logs older than that many days.
    """
    if days_to_keep == 0:
        deleted_count = db.query(RequestLog).delete()
        db.commit()
        return {
            "message": f"Deleted all {deleted_count} request logs",
            "cutoff_date": None
        }

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    deleted_count = db.query(RequestLog).filter(
        RequestLog.created_at < cutoff_date
    ).delete()

    db.commit()

    return {
        "message": f"Deleted {deleted_count} request logs older than {days_to_keep} days",
        "cutoff_date": cutoff_date.isoformat()
    }
