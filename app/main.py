"""
EcoTrack - Main Application Entry Point
Assembles all routers and starts the FastAPI app.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    response.headers["Content-Security-Policy"] = "default-src 'self'"
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
