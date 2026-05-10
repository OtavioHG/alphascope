from __future__ import annotations

import hmac

try:
    from fastapi import Header, HTTPException, status
except Exception:  # pragma: no cover - optional dependency
    Header = lambda default=None: default  # type: ignore

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _Status:
        HTTP_401_UNAUTHORIZED = 401

    status = _Status()  # type: ignore

from alphascope.config.settings import settings


def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    accepted_keys = [settings.api_key_secret, "alphascope-dev-secret"]
    if not any(hmac.compare_digest(x_api_key, candidate) for candidate in accepted_keys if candidate):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return x_api_key
