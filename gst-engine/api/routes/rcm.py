"""POST /v1/rcm/classify"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import require_api_key
from engine.rcm import classify_inward_invoice
from engine.rules_loader import get_rules

router = APIRouter(prefix="/v1/rcm", dependencies=[Depends(require_api_key)])


class RCMClassifyRequest(BaseModel):
    supplier_name: str
    supplier_gstin: str | None = None
    hsn_code: str | None = None


@router.post("/classify")
def rcm_classify(
    body: RCMClassifyRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    r = classify_inward_invoice(
        body.supplier_gstin, body.hsn_code, body.supplier_name,
        get_rules(effective_date),
    )
    return {
        "is_rcm": r.is_rcm,
        "rcm_reason": r.rcm_reason,
        "itc_blocked_reason": r.itc_blocked_reason,
        "is_import_of_service": r.is_import_of_service,
    }
