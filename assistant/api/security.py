"""Security middleware for Jarvis API."""

import time
import logging
from typing import List, Dict
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from assistant.config import get

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict API access to whitelisted IP addresses."""

    def __init__(self, app, allowed_ips: List[str]):
        super().__init__(app)
        self.allowed_ips = set(allowed_ips)
        logger.info(f"IP whitelist initialized with {len(self.allowed_ips)} addresses")

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host

        # Allow localhost
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            return await call_next(request)

        # Check whitelist
        if client_ip not in self.allowed_ips:
            logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Access denied for IP: {client_ip}"}
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        logger.info(f"Rate limiting enabled: {requests_per_minute} requests per minute")

    async def dispatch(self, request: Request, call_next):
        # Get identifier (IP + API key if present)
        client_ip = request.client.host
        api_key = request.headers.get("X-API-Key", "")
        identifier = f"{client_ip}:{api_key[:10]}"  # Use first 10 chars of key

        current_time = time.time()

        # Clean old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.window_size
        ]

        # Check rate limit
        if len(self.requests[identifier]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": int(self.window_size)
                }
            )

        # Add current request
        self.requests[identifier].append(current_time)

        response = await call_next(request)

        # Add rate limit headers
        remaining = self.requests_per_minute - len(self.requests[identifier])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
