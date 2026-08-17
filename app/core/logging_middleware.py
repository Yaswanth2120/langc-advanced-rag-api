"""Structured per-request access logging.

Emits one JSON log line per request to the ``app.access`` logger: method,
path, status code, duration, and client IP. This is the app's only
request-level observability today — there's no metrics endpoint or tracing
beyond optional LangSmith (see ``settings.langsmith_tracing``) — but it's
enough to answer "what happened" from log aggregation in any hosting
environment (Render, Docker, etc.) without adding an external dependency.
"""

import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                json.dumps(
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": request.client.host if request.client else None,
                    }
                )
            )
