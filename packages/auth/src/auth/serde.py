"""Serialization helpers (EPIC-A009)."""

from __future__ import annotations

from typing import Any, Mapping

from auth.models import AuthSession, AuthTokenPair, AuthUser

__all__ = [
    "session_to_dict",
    "token_pair_to_dict",
    "user_to_dict",
]


def user_to_dict(user: AuthUser | Mapping[str, Any], *, include_hash: bool = False) -> dict[str, Any]:
    if isinstance(user, AuthUser):
        return user.to_dict(include_hash=include_hash)
    row = dict(user)
    if not include_hash:
        row.pop("password_hash", None)
    return row


def session_to_dict(session: AuthSession | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(session, AuthSession):
        return session.to_public_dict()
    return dict(session)


def token_pair_to_dict(pair: AuthTokenPair | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(pair, AuthTokenPair):
        return pair.to_dict()
    return dict(pair)
