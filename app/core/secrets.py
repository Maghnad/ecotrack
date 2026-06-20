"""
EcoTrack - Google Cloud Secret Manager
Fetches API keys securely at runtime.
Falls back to .env values in testing/development mode.
"""
from app.core.config import get_settings

settings = get_settings()


def get_secret(secret_id: str) -> str:
    """
    Retrieve a secret value. Uses Secret Manager in production,
    falls back to environment variables in dev/test.
    """
    if settings.environment in ("testing", "development"):
        return getattr(settings, secret_id, "mock_key")

    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{settings.project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch secret '{secret_id}' from Secret Manager: {exc}"
        )
