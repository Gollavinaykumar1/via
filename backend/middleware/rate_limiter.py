# backend/middleware/rate_limiter.py
import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from backend.core.config import RATE_LIMIT_PER_MINUTE
from backend.core.logger import logger

_log: dict = defaultdict(list)

from fastapi.responses import JSONResponse

async def rate_limit_middleware(request: Request, call_next):
    skip = {
        "/", "/docs", "/openapi.json", "/redoc", "/health",
        "/via-chat.css", "/api/info",
        "/login_bg.png", "/login_bg.jpg",
        "/company_logo.png", "/company_logo.jpg",
        "/favicon.ico",
    }
    if request.url.path in skip or request.url.path.startswith("/ws"):
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _log[ip] = [t for t in _log[ip] if now - t < 60]
    if len(_log[ip]) >= RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Rate limit exceeded | IP: {ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded. Max {RATE_LIMIT_PER_MINUTE} req/min."}
        )
    _log[ip].append(now)
    return await call_next(request)
