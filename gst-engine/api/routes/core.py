"""
Core GST law endpoints:
  /v1/gstin/validate
  /v1/supply/type
  /v1/supply/tax
  /v1/itc/setoff
  /v1/itc/eligibility
  /v1/late-fee
  /v1/compliance/calendar
  /v1/turnover/aggregate
  /v1/composition/info
  /v1/credit-note/reversal
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import require_api_key
from engine.core import (
    validate_gstin,
    determine_supply_type,
    compute_tax_for_supply,
    compute_itc_setoff,
    check_itc_eligibility,
    compute_late_fee,
    get_compliance_calendar,
    compute_aggregate_turnover,
    get_composition_info,
    compute_credit_note_reversal,
)
from engine.rules_loader import get_rules

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])


def _d(v: float | str | None, default: str = "0") -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal(default)


def _rules(effective_date: date | None):
    return get_rules(effective_date)


# ── GSTIN Validate ────────────────────────────────────────────────────────────

class GSTINRequest(BaseModel):
    gstin: str

@router.post("/gstin/validate")
def gstin_validate(
    body: GSTINRequest,
    effective_date: date | None = Query(None, description="Rule version date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    valid, msg = validate_gstin(body.gstin, _rules(effective_date))
    return {"gstin": body.gstin.upper().strip(), "valid": valid, "message": msg}


# ── Supply Type ───────────────────────────────────────────────────────────────

class SupplyTypeRequest(BaseModel):
    business_state: str
    recipient_state: str

@router.post("/supply/type")
def supply_type(body: SupplyTypeRequest) -> dict[str, Any]:
    st = determine_supply_type(body.business_state, body.recipient_state)
    return {"supply_type": st, "business_state": body.business_state, "recipient_state": body.recipient_state}


# ── Tax for Supply ────────────────────────────────────────────────────────────

class SupplyTaxRequest(BaseModel):
    supply_type: str          # "intra" | "inter"
    taxable_value: float
    rate_pct: float

@router.post("/supply/tax")
def supply_tax(body: SupplyTaxRequest) -> dict[str, Any]:
    breakdown = compute_tax_for_supply(
        body.supply_type, _d(body.taxable_value), _d(body.rate_pct)  # type: ignore[arg-type]
    )
    return {
        "supply_type": body.supply_type,
        "taxable_value": body.taxable_value,
        "rate_pct": body.rate_pct,
        "igst": float(breakdown["igst"]),
        "cgst": float(breakdown["cgst"]),
        "sgst": float(breakdown["sgst"]),
        "total_tax": float(breakdown["igst"] + breakdown["cgst"] + breakdown["sgst"]),
    }


# ── ITC Set-Off ───────────────────────────────────────────────────────────────

class ITCSetoffRequest(BaseModel):
    igst_credit: float = 0.0
    cgst_credit: float = 0.0
    sgst_credit: float = 0.0
    igst_liability: float = 0.0
    cgst_liability: float = 0.0
    sgst_liability: float = 0.0

@router.post("/itc/setoff")
def itc_setoff(body: ITCSetoffRequest) -> dict[str, Any]:
    r = compute_itc_setoff(
        _d(body.igst_credit), _d(body.cgst_credit), _d(body.sgst_credit),
        _d(body.igst_liability), _d(body.cgst_liability), _d(body.sgst_liability),
    )
    return {
        "igst_credit_used": float(r.igst_credit_used),
        "cgst_credit_used": float(r.cgst_credit_used),
        "sgst_credit_used": float(r.sgst_credit_used),
        "igst_credit_remaining": float(r.igst_credit_remaining),
        "cgst_credit_remaining": float(r.cgst_credit_remaining),
        "sgst_credit_remaining": float(r.sgst_credit_remaining),
        "igst_cash_required": float(r.igst_cash_required),
        "cgst_cash_required": float(r.cgst_cash_required),
        "sgst_cash_required": float(r.sgst_cash_required),
        "total_cash_required": float(r.total_cash_required),
    }


# ── ITC Eligibility ───────────────────────────────────────────────────────────

class ITCEligibilityRequest(BaseModel):
    invoice_id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    itc_category: str | None = None
    is_rcm: bool = False
    check_date: date | None = None

@router.post("/itc/eligibility")
def itc_eligibility(
    body: ITCEligibilityRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    r = check_itc_eligibility(
        invoice_id=body.invoice_id,
        supplier_name=body.supplier_name,
        invoice_number=body.invoice_number,
        invoice_date=body.invoice_date,
        igst=_d(body.igst),
        cgst=_d(body.cgst),
        sgst=_d(body.sgst),
        itc_category=body.itc_category,
        is_rcm=body.is_rcm,
        check_date=body.check_date,
        rules=_rules(effective_date),
    )
    return {
        "invoice_id": r.invoice_id,
        "supplier_name": r.supplier_name,
        "invoice_number": r.invoice_number,
        "invoice_date": r.invoice_date.isoformat(),
        "igst": float(r.igst),
        "cgst": float(r.cgst),
        "sgst": float(r.sgst),
        "is_eligible": r.is_eligible,
        "blocked_reason": r.blocked_reason,
    }


# ── Late Fee ──────────────────────────────────────────────────────────────────

class LateFeeRequest(BaseModel):
    return_type: str           # "GSTR-1" | "GSTR-3B" | "GSTR-4" | "GSTR-9"
    period: str                # "YYYY-MM" or "YYYY-YY" for annual
    filing_date: date
    is_nil_return: bool = False
    annual_turnover: float | None = None

@router.post("/late-fee")
def late_fee(
    body: LateFeeRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    r = compute_late_fee(
        return_type=body.return_type,
        period=body.period,
        filing_date=body.filing_date,
        is_nil_return=body.is_nil_return,
        annual_turnover=_d(body.annual_turnover) if body.annual_turnover is not None else None,
        rules=_rules(effective_date),
    )
    return {
        "return_type": r.return_type,
        "period": r.period,
        "due_date": r.due_date.isoformat(),
        "filing_date": r.filing_date.isoformat(),
        "days_late": r.days_late,
        "late_fee_cgst": float(r.late_fee_cgst),
        "late_fee_sgst": float(r.late_fee_sgst),
        "late_fee_total": float(r.late_fee_total),
        "max_cap": float(r.max_cap),
        "is_nil_return": r.is_nil_return,
    }


# ── Compliance Calendar ────────────────────────────────────────────────────────

class ComplianceCalendarRequest(BaseModel):
    period: str
    is_composition: bool = False

@router.post("/compliance/calendar")
def compliance_calendar(
    body: ComplianceCalendarRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    items = get_compliance_calendar(body.period, body.is_composition, _rules(effective_date))
    return {
        "period": body.period,
        "is_composition": body.is_composition,
        "returns": [
            {
                "return_type": i.return_type,
                "period": i.period,
                "due_date": i.due_date.isoformat(),
                "days_remaining": i.days_remaining,
                "is_overdue": i.is_overdue,
                "late_fee_applicable": i.late_fee_applicable,
            }
            for i in items
        ],
    }


# ── Aggregate Turnover ────────────────────────────────────────────────────────

class AggregateTurnoverRequest(BaseModel):
    taxable_value: float = 0.0
    exempt_value: float = 0.0
    export_value: float = 0.0
    inter_state_value: float = 0.0
    state_code: str = "27"

@router.post("/turnover/aggregate")
def aggregate_turnover(
    body: AggregateTurnoverRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    r = compute_aggregate_turnover(
        _d(body.taxable_value), _d(body.exempt_value),
        _d(body.export_value), _d(body.inter_state_value),
        body.state_code, _rules(effective_date),
    )
    return {
        "taxable_value": float(r.taxable_value),
        "exempt_value": float(r.exempt_value),
        "export_value": float(r.export_value),
        "inter_state_value": float(r.inter_state_value),
        "aggregate_turnover": float(r.aggregate_turnover),
        "is_registration_required": r.is_registration_required,
        "registration_threshold": float(r.registration_threshold),
        "is_composition_eligible": r.is_composition_eligible,
        "state_code": r.state_code,
        "hsn_requirement": r.hsn_requirement,
    }


# ── Composition Info ──────────────────────────────────────────────────────────

class CompositionInfoRequest(BaseModel):
    aggregate_turnover: float
    business_type: str = "trader"   # trader | manufacturer | restaurant | other_services
    has_inter_state_supply: bool = False
    has_ecommerce_supply: bool = False

@router.post("/composition/info")
def composition_info(
    body: CompositionInfoRequest,
    effective_date: date | None = Query(None),
) -> dict[str, Any]:
    r = get_composition_info(
        _d(body.aggregate_turnover), body.business_type,
        body.has_inter_state_supply, body.has_ecommerce_supply,
        _rules(effective_date),
    )
    return {
        "is_eligible": r.is_eligible,
        "reason": r.reason,
        "applicable_rate_pct": float(r.applicable_rate) if r.applicable_rate is not None else None,
        "restrictions": r.restrictions,
        "return_form": r.return_form,
    }


# ── Credit Note Reversal ──────────────────────────────────────────────────────

class CreditNoteReversalRequest(BaseModel):
    credit_note_number: str
    discount_amount: float
    tax_rate_pct: float
    original_invoice_ref: str | None = None
    supply_type: str = "intra"        # "intra" | "inter"
    is_agreed_before_supply: bool = False

@router.post("/credit-note/reversal")
def credit_note_reversal(body: CreditNoteReversalRequest) -> dict[str, Any]:
    r = compute_credit_note_reversal(
        credit_note_number=body.credit_note_number,
        discount_amount=_d(body.discount_amount),
        tax_rate_pct=_d(body.tax_rate_pct),
        original_invoice_ref=body.original_invoice_ref,
        supply_type=body.supply_type,  # type: ignore[arg-type]
        is_agreed_before_supply=body.is_agreed_before_supply,
    )
    return {
        "credit_note_number": r.credit_note_number,
        "original_invoice_ref": r.original_invoice_ref,
        "reversal_igst": float(r.reversal_igst),
        "reversal_cgst": float(r.reversal_cgst),
        "reversal_sgst": float(r.reversal_sgst),
        "reversal_total": float(r.reversal_total),
        "is_traceable": r.is_traceable,
        "is_allowed": r.is_allowed,
        "reason": r.reason,
    }
