"""Central feature-flag registry and server-side checks."""
from fastapi import HTTPException, status

ADMIN_FEATURES = {
    "admin.users": "Gestionar usuarios",
    "admin.requests": "Moderar solicitudes",
    "admin.library": "Ver biblioteca completa",
    "admin.services": "Gestionar servicios",
    "admin.demo": "Modo demo",
}

# Product features are available to normal users when explicitly enabled by an
# administrator. They are not administrative powers and must never unlock
# /api/admin routes.
USER_FEATURES = {
    "replay.access": "Replay",
    "bingo.access": "Bingo musical",
}

ALL_FEATURES = {**ADMIN_FEATURES, **USER_FEATURES}


def effective_features(user) -> set[str]:
    if user.role == "ADMIN":
        return set(ALL_FEATURES)
    return {row.feature_key for row in user.feature_flags}


def has_feature(user, feature_key: str) -> bool:
    return feature_key in effective_features(user)


def require_feature(user, feature_key: str) -> None:
    if not has_feature(user, feature_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta función")
