"""
GSTR compute endpoints:
  POST /v1/gstr/1
  POST /v1/gstr/3b
  POST /v1/gstr/4
  POST /v1/gstr/9
  POST /v1/gstr/mismatch
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import require_api_key
from engine.gstr_compute import (
    OutwardInvoiceData,
    InwardInvoiceData,
    ReturnFilingData,
    compute_gstr1,
    compute_gstr3b,
    compute_gstr4,
    compute_gstr9,
    compute_mismatch,
)
from engine.rules_loader import get_rules

router = APIRouter(prefix="/v1/gstr", dependencies=[Depends(require_api_key)])


def _d(v: float | str | None, default: str = "0") -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal(default)


# ── Pydantic input models ─────────────────────────────────────────────────────

class OutwardInvoiceIn(BaseModel):
    invoice_type: str        # b2b | b2c_large | b2c_small | export | credit_note
    period: str
    taxable_value: float = 0.0
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    cess: float = 0.0

    def to_dataclass(self) -> OutwardInvoiceData:
        return OutwardInvoiceData(
            invoice_type=self.invoice_type, period=self.period,
            taxable_value=_d(self.taxable_value), igst=_d(self.igst),
            cgst=_d(self.cgst), sgst=_d(self.sgst), cess=_d(self.cess),
        )


class InwardInvoiceIn(BaseModel):
    id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    period: str
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    supplier_gstin: str | None = None
    itc_blocked_reason: str | None = None
    is_rcm: bool = False
    itc_2b_status: str = "unverified"

    def to_dataclass(self) -> InwardInvoiceData:
        return InwardInvoiceData(
            id=self.id, supplier_name=self.supplier_name,
            invoice_number=self.invoice_number, invoice_date=self.invoice_date,
            period=self.period, igst=_d(self.igst), cgst=_d(self.cgst), sgst=_d(self.sgst),
            supplier_gstin=self.supplier_gstin, itc_blocked_reason=self.itc_blocked_reason,
            is_rcm=self.is_rcm, itc_2b_status=self.itc_2b_status,
        )


class ReturnFilingIn(BaseModel):
    period: str
    return_type: str
    status: str
    total_tax_payable: float = 0.0
    itc_claimed: float = 0.0

    def to_dataclass(self) -> ReturnFilingData:
        return ReturnFilingData(
            period=self.period, return_type=self.return_type, status=self.status,
            total_tax_payable=_d(self.total_tax_payable), itc_claimed=_d(self.itc_claimed),
        )


# ── GSTR-1 ────────────────────────────────────────────────────────────────────

class GSTR1Request(BaseModel):
    period: str
    outward: list[OutwardInvoiceIn]

@router.post("/1")
def gstr1(body: GSTR1Request) -> dict[str, Any]:
    return compute_gstr1([i.to_dataclass() for i in body.outward], body.period)


# ── GSTR-3B ───────────────────────────────────────────────────────────────────

class GSTR3BRequest(BaseModel):
    period: str
    outward: list[OutwardInvoiceIn]
    inward: list[InwardInvoiceIn] = []
    reconciliation_done: bool = False

@router.post("/3b")
def gstr3b(
    body: GSTR3BRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    return compute_gstr3b(
        [i.to_dataclass() for i in body.outward],
        [i.to_dataclass() for i in body.inward],
        body.period,
        body.reconciliation_done,
        get_rules(effective_date),
    )


# ── GSTR-4 ────────────────────────────────────────────────────────────────────

class GSTR4Request(BaseModel):
    period: str
    business_type: str = "trader"    # trader | manufacturer | restaurant | other_services
    outward: list[OutwardInvoiceIn]
    inward: list[InwardInvoiceIn] = []

@router.post("/4")
def gstr4(
    body: GSTR4Request,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    return compute_gstr4(
        [i.to_dataclass() for i in body.outward],
        [i.to_dataclass() for i in body.inward],
        body.period,
        body.business_type,
        get_rules(effective_date),
    )


# ── GSTR-9 ────────────────────────────────────────────────────────────────────

class GSTR9Request(BaseModel):
    fy: str                          # e.g. "2024-25"
    outward: list[OutwardInvoiceIn]
    inward: list[InwardInvoiceIn] = []
    filed_returns: list[ReturnFilingIn] = []

@router.post("/9")
def gstr9(body: GSTR9Request) -> dict[str, Any]:
    return compute_gstr9(
        [i.to_dataclass() for i in body.outward],
        [i.to_dataclass() for i in body.inward],
        [r.to_dataclass() for r in body.filed_returns],
        body.fy,
    )


# ── Mismatch ──────────────────────────────────────────────────────────────────

class MismatchRequest(BaseModel):
    gstr1_payload: dict[str, Any]
    gstr3b_payload: dict[str, Any]

@router.post("/mismatch")
def mismatch(body: MismatchRequest) -> dict[str, Any]:
    return compute_mismatch(body.gstr1_payload, body.gstr3b_payload)
