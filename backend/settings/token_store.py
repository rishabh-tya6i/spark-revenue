from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import redis

from backend.config import settings


UPSTOX_TOKEN_KEY = "secrets:upstox:access_token"


@dataclass(frozen=True)
class TokenStatus:
    present: bool
    masked: str
    source: str  # "redis" | "env" | "missing"


def _redis_client() -> Optional[redis.Redis]:
    if not settings.REDIS_URL:
        return None
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _mask(token: str | None) -> str:
    if not token:
        return ""
    token = token.strip()
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


def get_upstox_token() -> str | None:
    """
    Returns the Upstox access token from Redis (preferred) or env (fallback).
    """
    r = _redis_client()
    if r:
        try:
            val = r.get(UPSTOX_TOKEN_KEY)
            if val:
                return val.strip()
        except Exception:
            # Fall back to env if Redis is unavailable
            pass
    return settings.UPSTOX_ACCESS_TOKEN.strip() if settings.UPSTOX_ACCESS_TOKEN else None


def set_upstox_token(token: str) -> None:
    r = _redis_client()
    if not r:
        raise RuntimeError("REDIS_URL not configured; cannot store token")
    token = (token or "").strip()
    if not token:
        raise ValueError("Token is empty")
    r.set(UPSTOX_TOKEN_KEY, token)


def clear_upstox_token() -> None:
    r = _redis_client()
    if not r:
        raise RuntimeError("REDIS_URL not configured; cannot clear token")
    r.delete(UPSTOX_TOKEN_KEY)


def get_upstox_token_status() -> TokenStatus:
    r = _redis_client()
    if r:
        try:
            val = r.get(UPSTOX_TOKEN_KEY)
            if val:
                return TokenStatus(present=True, masked=_mask(val), source="redis")
        except Exception:
            pass

    if settings.UPSTOX_ACCESS_TOKEN:
        return TokenStatus(present=True, masked=_mask(settings.UPSTOX_ACCESS_TOKEN), source="env")

    return TokenStatus(present=False, masked="", source="missing")

