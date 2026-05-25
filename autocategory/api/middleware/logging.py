"""
Request logging middleware
Automatically logs all API requests to database
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging

from database import SessionLocal
from models import RequestLog
from datetime import datetime

logger = logging.getLogger(__name__)


def _sanitize_request_body(raw: str | None, max_bytes: int = 4000) -> str | None:
    """Parse JSON request body, strip heavy fields (image_urls with base64/long URLs),
    then re-serialize to guarantee valid JSON is stored. Falls back to plain truncation."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
        # Remove or truncate image_urls — can be large base64 strings
        if isinstance(data, dict) and "image_urls" in data:
            urls = data["image_urls"]
            if isinstance(urls, list):
                data["image_urls"] = [u[:80] + "..." if len(u) > 80 else u for u in urls]
        serialized = json.dumps(data, ensure_ascii=False)
        return serialized[:max_bytes] if len(serialized) > max_bytes else serialized
    except Exception:
        # If not valid JSON (shouldn't happen) just truncate safely
        return raw[:max_bytes]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests to database
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details
        """
        # Start timing
        start_time = time.time()
        
        # Get request details
        method = request.method
        endpoint = str(request.url.path)
        
        # Skip logging for certain endpoints (including SSE streaming endpoints)
        skip_endpoints = ["/docs", "/redoc", "/openapi.json", "/api/health"]
        if endpoint in skip_endpoints or endpoint.endswith("/stream"):
            return await call_next(request)
        
        # Get request body (if JSON)
        request_body = None
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body_bytes = await request.body()
                if body_bytes:
                    request_body = body_bytes.decode('utf-8')
                    # Store body back for route handlers
                    # Must return http.disconnect on 2nd call to avoid Starlette middleware crash
                    _body_consumed = False
                    async def receive(_consumed=None):
                        nonlocal _body_consumed
                        if not _body_consumed:
                            _body_consumed = True
                            return {"type": "http.request", "body": body_bytes, "more_body": False}
                        return {"type": "http.disconnect"}
                    request._receive = receive
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")
        
        # Get user info from request state (set by auth middleware)
        api_key_id = getattr(request.state, "api_key_id", None)
        user_id = getattr(request.state, "user_id", None)
        
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Process request
        response = None
        error_message = None
        status_code = None
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"Request failed: {e}")
            error_message = str(e)
            status_code = 500
            # Re-raise to let FastAPI error handler deal with it
            raise
        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract classification details if available
            classification_data = {}
            if hasattr(request.state, "classification_result"):
                result = request.state.classification_result
                classification_data = {
                    "input_title": result.get("input_title"),
                    "input_description": result.get("input_description"),
                    "predicted_category_id": result.get("predicted_category_id"),
                    "predicted_category_name": result.get("predicted_category_name"),
                    "predicted_category_path": result.get("predicted_category_path"),
                    "confidence": result.get("confidence"),
                    "decision": result.get("decision"),
                    "llm_reason": result.get("llm_reason"),  # LLM reasoning from rerank
                }
                # Store full result for potential training data creation
                # (including llm_reason and understanding_output)
                request.state.full_classification_result = result
            
            # Log to database asynchronously
            try:
                db = SessionLocal()
                log_entry = RequestLog(
                    api_key_id=api_key_id,
                    user_id=user_id,
                    endpoint=endpoint,
                    method=method,
                    request_body=_sanitize_request_body(request_body),  # Strip large fields, keep valid JSON
                    response_status=status_code,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,  # Limit size
                    **classification_data
                )
                db.add(log_entry)
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Failed to log request to database: {e}")
        
        return response
