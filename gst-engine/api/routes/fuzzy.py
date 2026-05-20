"""
Fuzzy match endpoints:
  POST /v1/fuzzy/match-pair
  POST /v1/fuzzy/find-best
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import require_api_key
from engine.fuzzy import reconcile_pair, find_best_match

router = APIRouter(prefix="/v1/fuzzy", dependencies=[Depends(require_api_key)])


def _match_result_dict(r: Any) -> dict:
    return {
        "confidence": r.confidence,
        "match_type": r.match_type,
        "normalized_source": r.normalized_source,
        "normalized_target": r.normalized_target,
    }


class MatchPairRequest(BaseModel):
    source_name: str
    target_name: str
    source_gstin: str | None = None
    target_gstin: str | None = None


@router.post("/match-pair")
def match_pair(body: MatchPairRequest) -> dict[str, Any]:
    r = reconcile_pair(body.source_gstin, body.source_name, body.target_gstin, body.target_name)
    return _match_result_dict(r)


class SupplierEntry(BaseModel):
    name: str
    gstin: str | None = None


class FindBestRequest(BaseModel):
    source: SupplierEntry
    candidates: list[SupplierEntry]
    threshold: int = 75


@router.post("/find-best")
def find_best(body: FindBestRequest) -> dict[str, Any]:
    best, result = find_best_match(
        {"name": body.source.name, "gstin": body.source.gstin},
        [{"name": c.name, "gstin": c.gstin} for c in body.candidates],
        body.threshold,
    )
    return {
        "matched": best is not None,
        "best_candidate": best,
        "result": _match_result_dict(result),
    }
