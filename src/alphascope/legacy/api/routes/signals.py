from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends

from alphascope.security.api_keys import verify_api_key
from alphascope.security.rate_limit import rate_limit_dependency

router = APIRouter()


@router.get("/signals")
def get_signals(
    _: str = Depends(verify_api_key),
    __: None = Depends(rate_limit_dependency()),
):
    predictions_dir = Path("data/processed/predictions")
    files = sorted(predictions_dir.glob("predictions_*.csv"), key=lambda item: item.stat().st_mtime)
    if not files:
        return []
    return pd.read_csv(files[-1]).to_dict(orient="records")
