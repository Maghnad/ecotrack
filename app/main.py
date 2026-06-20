"""
EcoTrack - Main Application Entry Point
Assembles all routers and starts the FastAPI app.
"""

import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import actions, footprint, users

app = FastAPI(
    title="EcoTrack API",
    description=(
        "**EcoTrack** helps individuals understand, track, and reduce their carbon footprint "
        "through simple logging, personalised AI insights, gamification, and weekly challenges.\n\n"
        "**Authentication:** All endpoints (except `/health`) require a Firebase Bearer token "
        "in the `Authorization` header. Use `mock_token` in the testing environment.\n\n"
        "**Google Products Used:** Firebase Auth · Cloud Firestore · Maps Platform · "
        "Gemini AI · Cloud Secret Manager · (Proposed) Cloud Run"
    ),
    version="2.0.0",
    contact={"name": "EcoTrack Team"},
    license_info={"name": "MIT"},
)

# Configure Rate Limiter (100 requests per minute)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure JSON Audit Logger for SIEM integration
audit_logger = logging.getLogger("audit_log")
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    audit_logger.addHandler(ch)

# Allow frontend apps to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://ecotrack-00001-ks7.us-central1.run.app",
        "https://ecotrack-500009.web.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Allow CDNs for fonts, charts, 3D, and inline scripts/styles
    csp = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
        "https://fonts.googleapis.com https://fonts.gstatic.com"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Extract UID from token if available
    auth_header = request.headers.get("Authorization", "")
    uid = "anonymous"
    if auth_header.startswith("Bearer mock_token_"):
        uid = f"uid_{auth_header.split('mock_token_')[1]}"
    elif auth_header == "Bearer mock_token":
        uid = "mock_user_123"

    audit_event = {
        "timestamp": time.time(),
        "event_type": "HTTP_REQUEST",
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "unknown",
        "user_uid": uid,
        "status_code": response.status_code,
        "latency_ms": round(process_time * 1000, 2)
    }
    audit_logger.info(json.dumps(audit_event))
    return response

# Register routers
app.include_router(footprint.router)
app.include_router(users.router)
app.include_router(actions.router)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Public health check. Returns service status and version."""
    return {"status": "ok", "service": "ecotrack-api", "version": "2.0.0"}


# Mount the frontend UI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
