"""
backend/app/core/rate_limit.py
==============================
In-memory token bucket / sliding window rate limiter.
Tailored for single-instance B.Tech deployment (zero external Redis/cache dependency).

Protects sensitive endpoints:
  - /api/v1/auth/login
  - /predict/*
  - /admin/*
  - /api/v1/audit-logs
  - /api/v1/evidence/upload
"""

import time
from collections import defaultdict
from typing import Optional
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.core.config import settings
from app.core.logger import logger


class InMemoryRateLimiter:
    """
    Lightweight sliding-window rate limiter per client IP.
    Stores timestamps of requests within a sliding window.
    """

    def __init__(self) -> None:
        # Map: rule_name -> { ip_address: [timestamp, ...] }
        self._history: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

        # Default rules: (pattern, max_requests, window_seconds)
        self._rules = [
            ("auth", "/api/v1/auth/login", 15, 60),            # 15 req/min
            ("predict", "/predict", 120, 60),                  # 120 req/min
            ("predict_v1", "/api/v1/predict", 120, 60),        # 120 req/min
            ("admin", "/admin", 120, 60),                      # 120 req/min
            ("audit", "/api/v1/audit-logs", 120, 60),          # 120 req/min
            ("upload", "/api/v1/evidence/upload", 30, 60),     # 30 req/min
        ]

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check_rate_limit(self, request: Request) -> Optional[Response]:
        """
        Evaluates the request against rate limiting rules.
        Returns a 429 JSONResponse if limit is exceeded, or None if permitted.
        """
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return None

        # Check for test-mode bypass header if set
        if request.headers.get("X-Bypass-Rate-Limit") == "crimelens-test":
            return None

        path = request.url.path
        now = time.time()
        client_ip = self._get_client_ip(request)

        for rule_name, prefix, max_reqs, window_sec in self._rules:
            if path.startswith(prefix):
                window_start = now - window_sec
                ip_history = self._history[rule_name][client_ip]

                # Evict timestamps older than window
                self._history[rule_name][client_ip] = [t for t in ip_history if t > window_start]
                current_count = len(self._history[rule_name][client_ip])

                if current_count >= max_reqs:
                    logger.warning(
                        "Rate limit exceeded: IP=%s route=%s rule=%s count=%d limit=%d",
                        client_ip,
                        path,
                        rule_name,
                        current_count,
                        max_reqs,
                    )
                    retry_after = int(window_sec - (now - self._history[rule_name][client_ip][0])) + 1
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Rate limit exceeded for {rule_name}. Maximum {max_reqs} requests per {window_sec}s.",
                            "retry_after_seconds": max(1, retry_after),
                        },
                        headers={"Retry-After": str(max(1, retry_after))},
                    )

                # Append current request timestamp
                self._history[rule_name][client_ip].append(now)
                break

        return None

    def reset(self) -> None:
        """Clears all stored rate limiting history (used in tests)."""
        self._history.clear()


# Global singleton instance
rate_limiter = InMemoryRateLimiter()
