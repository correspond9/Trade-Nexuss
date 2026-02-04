"""
Rate Limiting Middleware
Handles rate limiting for API endpoints
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Dict, List, Any
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware with different limits per endpoint"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Rate limits per endpoint (requests per minute)
        self.rate_limits = {
            "/api/v1/auth/login": 5,      # 5 login attempts per minute
            "/api/v1/auth/register": 3,   # 3 registrations per minute
            "/api/v1/trading/orders": 60, # 60 orders per minute
            "/api/v1/market/quote": 100,  # 100 quotes per minute
            "default": 100                # 100 requests per minute for other endpoints
        }
        
        # Client request tracking
        self.clients: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.window_size = 60  # 1 minute window
    
    def get_rate_limit(self, path: str) -> int:
        """Get rate limit for specific path"""
        for pattern, limit in self.rate_limits.items():
            if pattern != "default" and pattern in path:
                return limit
        return self.rate_limits["default"]
    
    def is_rate_limited(self, client_id: str, path: str) -> tuple[bool, int]:
        """Check if client is rate limited"""
        current_time = time.time()
        rate_limit = self.get_rate_limit(path)
        
        # Get client's requests for this endpoint
        requests = self.clients[client_id][path]
        
        # Remove old requests outside the window
        while requests and requests[0] < current_time - self.window_size:
            requests.popleft()
        
        # Check if rate limit exceeded
        if len(requests) >= rate_limit:
            return True, rate_limit
        
        # Add current request
        requests.append(current_time)
        return False, rate_limit
    
    async def dispatch(self, request: Request, call_next):
        client_id = request.client.host
        path = request.url.path
        
        # Check rate limit
        is_limited, rate_limit = self.is_rate_limited(client_id, path)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_id} on {path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(rate_limit),
                    "X-RateLimit-Window": str(self.window_size)
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        current_requests = len(self.clients[client_id][path])
        remaining = max(0, rate_limit - current_requests)
        
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_size)
        
        return response

class TokenBucketRateLimit:
    """Token bucket rate limiting algorithm"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available"""
        current_time = time.time()
        
        # Refill tokens based on time passed
        time_passed = current_time - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_refill = current_time
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_available_tokens(self) -> int:
        """Get available tokens"""
        current_time = time.time()
        time_passed = current_time - self.last_refill
        return min(self.capacity, int(self.tokens + time_passed * self.refill_rate))
