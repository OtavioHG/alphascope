from __future__ import annotations

from fastapi import APIRouter, Depends

from alphascope.dashboard.services.trading_service import TradingService
from alphascope.security.api_keys import verify_api_key
from alphascope.security.rate_limit import rate_limit_dependency

router = APIRouter()


@router.get("/trades")
def get_trades(
    _: str = Depends(verify_api_key),
    __: None = Depends(rate_limit_dependency()),
):
    return TradingService().load_trades().to_dict(orient="records")
