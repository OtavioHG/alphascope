from __future__ import annotations

from fastapi import APIRouter, Depends

from alphascope.dashboard.services.ranking_service import RankingService
from alphascope.security.api_keys import verify_api_key
from alphascope.security.rate_limit import rate_limit_dependency

router = APIRouter()


@router.get("/ranking")
def get_ranking(
    _: str = Depends(verify_api_key),
    __: None = Depends(rate_limit_dependency()),
):
    return RankingService().load_latest_ranking().to_dict(orient="records")
