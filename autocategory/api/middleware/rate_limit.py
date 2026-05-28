"""
Rate limiting middleware using Redis
"""
import time
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import logging

from config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis
    """
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        # Initialize Redis client
        if redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Rate limiter connected to Redis")
            except Exception as e:
                logger.warning(f"Redis connection failed, rate limiting disabled: {e}")
                self.redis_client = None
        else:
            self.redis_client = redis_client
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits before processing request
        """
        # Skip rate limiting if Redis is not available
        if self.redis_client is None:
            return await call_next(request)
        
        # Skip rate limiting for certain endpoints
        skip_endpoints = ["/docs", "/redoc", "/openapi.json", "/api/health",
                          "/api/auth/login", "/api/auth/refresh", "/api/auth/logout"]
        if request.url.path in skip_endpoints:
            return await call_next(request)
        
        # Get API key info from request state (set by auth middleware)
        api_key_id = getattr(request.state, "api_key_id", None)
        rate_limit_per_minute = getattr(request.state, "rate_limit_per_minute", None)
        rate_limit_per_day = getattr(request.state, "rate_limit_per_day", None)
        
        # If no API key, use IP-based rate limiting
        if api_key_id is None:
            identifier = request.client.host if request.client else "unknown"
            rate_limit_per_minute = settings.default_rate_limit_per_minute
            rate_limit_per_day = settings.default_rate_limit_per_day
        else:
            identifier = f"api_key:{api_key_id}"
        
        # Check rate limits (Redis only — call_next is outside this block)
        minute_count = 0
        day_count = 0
        try:
            # Per-minute limit
            minute_key = f"rate_limit:minute:{identifier}:{int(time.time() // 60)}"
            minute_count = self.redis_client.incr(minute_key)

            if minute_count == 1:
                self.redis_client.expire(minute_key, 60)

            if minute_count > rate_limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {rate_limit_per_minute} requests per minute"
                )

            # Per-day limit
            day_key = f"rate_limit:day:{identifier}:{int(time.time() // 86400)}"
            day_count = self.redis_client.incr(day_key)

            if day_count == 1:
                self.redis_client.expire(day_key, 86400)

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
