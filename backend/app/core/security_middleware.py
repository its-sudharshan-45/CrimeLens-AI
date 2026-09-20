"""
backend/app/core/security_middleware.py
=======================================
Comprehensive HTTP Security, Correlation ID, and Observability Middleware.
"""

from time import perf_counter
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logger import logger
from app.core.rate_limit import rate_limiter


class SecurityHeadersAndObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware providing:
      1. Request correlation ID (X-Request-ID).
      2. Security response headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
      3. In-memory rate limiting check.
      4. Request latency measurement and Server-Timing header.
      5. Structured access logging.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Correlation / Request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # 2. Rate limit check
        rate_limit_resp = rate_limiter.check_rate_limit(request)
        if rate_limit_resp is not None:
            rate_limit_resp.headers["X-Request-ID"] = request_id
            return rate_limit_resp

        # 3. Execution timing
        start_time = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (perf_counter() - start_time) * 1000
            logger.exception(
                "Unhandled exception processing HTTP %s %s [ReqID: %s] after %.1f ms: %s",
                request.method,
                request.url.path,
                request_id,
                duration_ms,
                exc,
            )
            raise

        duration_ms = (perf_counter() - start_time) * 1000

        # 4. Security Headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"

        # Safe Content-Security-Policy
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https:; "
                "connect-src 'self' http: https: ws: wss:; "
                "frame-ancestors 'none';"
            )

        # 5. Structured logging
        logger.info(
            "HTTP %s %s -> %s [ReqID: %s] in %.1f ms",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            duration_ms,
        )

        return response
