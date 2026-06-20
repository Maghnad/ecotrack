"""
EcoTrack - Firestore Database Service
All read/write operations are encapsulated here.
The rest of the app never touches Firestore directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Any

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# In-memory mock store (used when ENVIRONMENT=testing)
# ---------------------------------------------------------------------------
_MOCK_DB: dict[str, dict] = {}


def _mock_collection(path: str) -> dict:
    return _MOCK_DB.setdefault(path, {})


def _get_firestore_client():
    """Returns a real Firestore client, or None in testing mode."""
    if settings.environment == "testing":
        return None
    import firebase_admin
    from firebase_admin import firestore as fs

    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return fs.client()


# ---------------------------------------------------------------------------
# User profile helpers
# ---------------------------------------------------------------------------


def get_user_profile(uid: str) -> Optional[dict]:
    if settings.environment == "testing":
        return _MOCK_DB.get(f"users/{uid}")
    db = _get_firestore_client()
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def upsert_user_profile(uid: str, data: dict) -> None:
    if settings.environment == "testing":
        existing = _MOCK_DB.get(f"users/{uid}", {})
        existing.update(data)
        _MOCK_DB[f"users/{uid}"] = existing
        return
    db = _get_firestore_client()
    db.collection("users").document(uid).set(data, merge=True)


def ensure_user_exists(uid: str, email: Optional[str]) -> dict:
    """Create a new user profile with defaults if it doesn't already exist."""
    profile = get_user_profile(uid)
    if profile:
        return profile
    now = datetime.utcnow().isoformat()
    new_profile: dict[str, Any] = {
        "uid": uid,
        "email": email,
        "display_name": email.split("@")[0] if email else "EcoUser",
        "total_xp": 0,
        "level": 0,
        "streak_days": 0,
        "longest_streak": 0,
        "last_log_date": None,
        "total_carbon_saved_kg": 0.0,
        "badges": [],
        "created_at": now,
    }
    upsert_user_profile(uid, new_profile)
    return new_profile


# ---------------------------------------------------------------------------
# Footprint log helpers
# ---------------------------------------------------------------------------


def save_footprint_log(uid: str, log_data: dict) -> str:
    """Persist a footprint log entry and return its auto-generated ID."""
    log_id = f"log_{uid}_{datetime.utcnow().timestamp():.0f}"
    log_data["log_id"] = log_id
    log_data["uid"] = uid
    log_data["logged_at"] = datetime.utcnow().isoformat()

    if settings.environment == "testing":
        collection_key = f"footprint_logs/{uid}"
        _mock_collection(collection_key)[log_id] = log_data
        return log_id

    db = _get_firestore_client()
    ref = (
        db.collection("footprint_logs")
        .document(uid)
        .collection("logs")
        .document(log_id)
    )
    ref.set(log_data)
    return log_id


def get_user_logs(uid: str, days: int = 7) -> list[dict]:
    """Retrieve the last `days` days of logs for a user."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    if settings.environment == "testing":
        collection_key = f"footprint_logs/{uid}"
        logs = list(_mock_collection(collection_key).values())
        return [
            log_entry for log_entry in logs if log_entry.get("logged_at", "") >= cutoff
        ]

    db = _get_firestore_client()
    docs = (
        db.collection("footprint_logs")
        .document(uid)
        .collection("logs")
        .where("logged_at", ">=", cutoff)
        .stream()
    )
    return [d.to_dict() for d in docs]


# ---------------------------------------------------------------------------
# Leaderboard helpers
# ---------------------------------------------------------------------------


def get_leaderboard(limit: int = 10) -> list[dict]:
    """Return top users by XP."""
    if settings.environment == "testing":
        users = [v for k, v in _MOCK_DB.items() if k.startswith("users/")]
        return sorted(users, key=lambda u: u.get("total_xp", 0), reverse=True)[:limit]

    db = _get_firestore_client()
    docs = (
        db.collection("users")
        .order_by("total_xp", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


# ---------------------------------------------------------------------------
# Challenge helpers
# ---------------------------------------------------------------------------


def save_challenge_progress(uid: str, challenge_id: str, progress: dict) -> None:
    key = f"challenge_progress/{uid}/{challenge_id}"
    if settings.environment == "testing":
        _MOCK_DB[key] = progress
        return
    db = _get_firestore_client()
    db.collection("challenge_progress").document(uid).collection("challenges").document(
        challenge_id
    ).set(progress)


def get_challenge_progress(uid: str, challenge_id: str) -> Optional[dict]:
    key = f"challenge_progress/{uid}/{challenge_id}"
    if settings.environment == "testing":
        return _MOCK_DB.get(key)
    db = _get_firestore_client()
    doc = (
        db.collection("challenge_progress")
        .document(uid)
        .collection("challenges")
        .document(challenge_id)
        .get()
    )
    return doc.to_dict() if doc.exists else None
