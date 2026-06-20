"""
EcoTrack - Security & Authentication
Validates Firebase JWT tokens on every protected route.
In testing/mock mode, accepts a dummy token for local development.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Dependency that extracts and validates the Firebase bearer token.
    Returns a dict with at least {"uid": str, "email": str | None, "role": str}.
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
            return {"uid": f"uid_{username}", "email": f"{username}@ecotrack.app", "role": "user"}
        elif token == "mock_token":
            return {"uid": "mock_user_123", "email": "dev@ecotrack.app", "role": "admin"}

    # --- Production: validate with Firebase Admin SDK ---
    try:
        import firebase_admin.auth as fb_auth

        decoded = fb_auth.verify_id_token(token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "role": decoded.get("role", "user")
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(
    current_user: dict = Security(get_current_user),
) -> dict:
    """
    Enforces Role-Based Access Control (RBAC).
    Rejects the request if the current user does not have the 'admin' role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required.",
        )
    return current_user
