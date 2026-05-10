from __future__ import annotations

try:
    from .api_keys import verify_api_key
    from .auth import create_jwt_token, verify_jwt_token
    from .rate_limit import RateLimiter, rate_limit_dependency
except Exception:  # pragma: no cover - optional FastAPI dependency in lightweight envs
    verify_api_key = None
    create_jwt_token = None
    verify_jwt_token = None
    RateLimiter = None
    rate_limit_dependency = None

__all__ = [
    "verify_api_key",
    "create_jwt_token",
    "verify_jwt_token",
    "RateLimiter",
    "rate_limit_dependency",
]
