"""Administration of product-feature rollout audiences."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.features import USER_FEATURES
from app.models.feature_rollout import FeatureRollout
from app.models.user import User, UserFeatureFlag

VALID_MODES = {"off", "friends", "global"}


def _upsert_mode(db: DbSession, feature_key: str, mode: str) -> None:
    rollout = db.get(FeatureRollout, feature_key)
    if rollout is None:
        db.add(FeatureRollout(feature_key=feature_key, mode=mode))
    else:
        rollout.mode = mode


def list_rollouts(db: DbSession) -> list[dict]:
    users = list(db.scalars(select(User).where(User.role == "USER").order_by(User.username)).all())
    rows = {row.feature_key: row for row in db.scalars(select(FeatureRollout)).all()}
    flags = list(db.scalars(select(UserFeatureFlag).where(UserFeatureFlag.feature_key.in_(USER_FEATURES))).all())
    usernames_by_feature: dict[str, set[str]] = {key: set() for key in USER_FEATURES}
    names_by_id = {user.id: user.username for user in users}
    for flag in flags:
        username = names_by_id.get(flag.user_id)
        if username:
            usernames_by_feature.setdefault(flag.feature_key, set()).add(username)
    return [
        {
            "key": key,
            "label": label,
            # Old installations may already have direct grants. Treat them as
            # Friends & Family until an admin deliberately changes the mode.
            "mode": rows[key].mode if key in rows else ("friends" if usernames_by_feature[key] else "off"),
            "usernames": sorted(usernames_by_feature[key]),
        }
        for key, label in USER_FEATURES.items()
    ]


def set_rollout(db: DbSession, *, feature_key: str, mode: str, usernames: list[str]) -> dict:
    if feature_key not in USER_FEATURES:
        raise ValueError("Feature no válida")
    if mode not in VALID_MODES:
        raise ValueError("Modo de activación no válido")

    users = list(db.scalars(select(User).where(User.role == "USER").order_by(User.username)).all())
    by_username = {user.username.lower(): user for user in users}
    requested = {username.strip().lstrip("@").lower() for username in usernames if username.strip()}
    unknown = requested.difference(by_username)
    if unknown:
        raise ValueError(f"No existe el alias @{sorted(unknown)[0]}")

    target_ids = (
        {user.id for user in users}
        if mode == "global"
        else {by_username[username].id for username in requested}
        if mode == "friends"
        else set()
    )
    db.query(UserFeatureFlag).filter(UserFeatureFlag.feature_key == feature_key).delete()
    db.add_all([UserFeatureFlag(user_id=user_id, feature_key=feature_key) for user_id in target_ids])
    _upsert_mode(db, feature_key, mode)
    db.commit()
    return next(item for item in list_rollouts(db) if item["key"] == feature_key)


def global_feature_keys(db: DbSession) -> set[str]:
    return {
        row.feature_key
        for row in db.scalars(select(FeatureRollout).where(FeatureRollout.mode == "global")).all()
        if row.feature_key in USER_FEATURES
    }
