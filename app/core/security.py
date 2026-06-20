"""
EcoTrack - Security & Authentication
Validates Firebase JWT tokens on every protected route.
In testing/mock mode, accepts a dummy token for local development.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Dependency that extracts and validates the Firebase bearer token.
    Returns a dict with at least {"uid": str, "email": str | None}.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # --- Mock mode for local dev / tests ---
    if settings.environment in ("testing", "development"):
        if token.startswith("mock_token_"):
            username = token.split("mock_token_")[1]
            return {"uid": f"uid_{username}", "email": f"{username}@ecotrack.app"}
        elif token == "mock_token":
            return {"uid": "mock_user_123", "email": "dev@ecotrack.app"}

    # --- Production: validate with Firebase Admin SDK ---
    try:
        import firebase_admin.auth as fb_auth
        decoded = fb_auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email")}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
