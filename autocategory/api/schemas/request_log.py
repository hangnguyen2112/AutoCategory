"""
Pydantic schemas for request logs
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class RequestLogBase(BaseModel):
    """Base request log schema"""
    endpoint: str
    method: str


class RequestLogResponse(RequestLogBase):
    """Schema for request log response"""
    id: int
    api_key_id: Optional[int]
    user_id: Optional[int]
    request_body: Optional[str]
    response_status: Optional[int]
    response_time_ms: Optional[float]
    error_message: Optional[str]
    
    # Classification details
    input_title: Optional[str]
    input_description: Optional[str]
    predicted_category_id: Optional[int]
    predicted_category_name: Optional[str]
    predicted_category_path: Optional[str]
    confidence: Optional[float]
    decision: Optional[str]
    llm_reason: Optional[str]  # LLM reasoning from rerank step
    
    # Feedback
    actual_category_id: Optional[int]
    was_corrected: Optional[bool]
    
    # Metadata
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RequestLogFilter(BaseModel):
    """Schema for filtering request logs"""
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    user_id: Optional[int] = None
    api_key_id: Optional[int] = None
    min_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    has_error: Optional[bool] = None
    was_corrected: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class RequestLogStats(BaseModel):
    """Schema for request log statistics"""
    total_requests: int
    success_rate: float
    avg_response_time: float
    error_count: int
    correction_rate: float
    requests_by_endpoint: dict
    requests_by_status: dict
    top_categories: list
    top_reasons: list = []  # LLM rerank reasons


class RequestLogListResponse(BaseModel):
    """Paginated request log list response"""
    items: list[RequestLogResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
