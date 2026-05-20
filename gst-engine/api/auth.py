"""
API key authentication dependency.
Keys stored in GST_ENGINE_API_KEYS env var (comma-separated).
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_KEY_HEADER = APIKeyHeader(name="X-Api-Key", auto_error=False)


def _load_keys() -> set[str]:
    raw = os.environ.get("GST_ENGINE_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def require_api_key(api_key: str | None = Security(_KEY_HEADER)) -> str:
    keys = _load_keys()
    if not keys:
        # Dev mode: no keys configured → allow all
        return api_key or "dev"
    if not api_key or api_key not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
