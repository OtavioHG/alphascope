from __future__ import annotations

from fastapi import APIRouter, Depends

from alphascope.monitoring.system_status import SystemStatusService
from alphascope.security.api_keys import verify_api_key
from alphascope.security.rate_limit import rate_limit_dependency

router = APIRouter()


@router.get("/portfolio")
def get_portfolio(
    _: str = Depends(verify_api_key),
    __: None = Depends(rate_limit_dependency()),
):
    return SystemStatusService().get_status().get("portfolio", {})
