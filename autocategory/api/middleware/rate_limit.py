"""
Rate limiting middleware using Redis
"""
import time
import hashlib
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits before processing request
        """
        # Skip rate limiting if Redis is not available
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client is None:
            return await call_next(request)
        
        # Skip rate limiting for certain endpoints
        skip_endpoints = ["/docs", "/redoc", "/openapi.json", "/api/health",
                          "/api/auth/login", "/api/auth/refresh", "/api/auth/logout"]
        if request.url.path in skip_endpoints:
            return await call_next(request)
        
        # Dependencies execute after middleware, so request.state cannot contain
        # API-key metadata here. Hash the presented key to create a stable,
        # non-secret bucket; unauthenticated requests fall back to client IP.
        presented_key = request.headers.get("x-api-key")
        if presented_key:
            key_id = hashlib.sha256(presented_key.encode()).hexdigest()[:32]
            identifier = f"api_key:{key_id}"
        else:
            identifier = request.client.host if request.client else "unknown"
        rate_limit_per_minute = settings.default_rate_limit_per_minute
        rate_limit_per_day = settings.default_rate_limit_per_day
        
        # Check rate limits (Redis only — call_next is outside this block)
        minute_count = 0
        day_count = 0
        try:
            # Per-minute limit
            minute_key = f"rate_limit:minute:{identifier}:{int(time.time() // 60)}"
            day_key = f"rate_limit:day:{identifier}:{int(time.time() // 86400)}"
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.incr(minute_key)
                pipe.expire(minute_key, 60)
                pipe.incr(day_key)
                pipe.expire(day_key, 86400)
                minute_count, _, day_count, _ = await pipe.execute()

            if minute_count > rate_limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {rate_limit_per_minute} requests per minute"
                )

            if day_count > rate_limit_per_day:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {rate_limit_per_day} requests per day"
                )

        except HTTPException:
            raise
        except Exception as e:
            # Redis error — log and allow request through without rate limiting
            logger.error(f"Rate limiting error: {e}")

        # Process the actual request (outside try-except so errors are not swallowed)
        response = await call_next(request)

        # Attach rate limit headers if counts were tracked
        if minute_count and rate_limit_per_minute:
            response.headers["X-RateLimit-Limit-Minute"] = str(rate_limit_per_minute)
            response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, rate_limit_per_minute - minute_count))
        if day_count and rate_limit_per_day:
            response.headers["X-RateLimit-Limit-Day"] = str(rate_limit_per_day)
            response.headers["X-RateLimit-Remaining-Day"] = str(max(0, rate_limit_per_day - day_count))

        return response
