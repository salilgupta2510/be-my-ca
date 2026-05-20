"""POST /v1/risk/score"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import require_api_key
from engine.risk import compute_risk_score

router = APIRouter(prefix="/v1/risk", dependencies=[Depends(require_api_key)])


def _d(v: float) -> Decimal:
    return Decimal(str(v))


class RiskScoreRequest(BaseModel):
    declared_income: float
    total_cash_deposits: float = 0.0
    total_high_value_purchases: float = 0.0
    total_credits: float = 0.0
    gst_mismatch_count: int = 0
    itc_reversal_risk_amount: float = 0.0
    has_foreign_transactions: bool = False


@router.post("/score")
def risk_score(body: RiskScoreRequest) -> dict[str, Any]:
    r = compute_risk_score(
        declared_income=_d(body.declared_income),
        total_cash_deposits=_d(body.total_cash_deposits),
        total_high_value_purchases=_d(body.total_high_value_purchases),
        total_credits=_d(body.total_credits),
        gst_mismatch_count=body.gst_mismatch_count,
        itc_reversal_risk_amount=_d(body.itc_reversal_risk_amount),
        has_foreign_transactions=body.has_foreign_transactions,
    )
    return {
        "overall_score": r.overall_score,
        "level": r.level,
        "factors": r.factors,
    }
