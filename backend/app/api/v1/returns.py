import asyncio
import random
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.business import Business
from app.models.invoice import OutwardInvoice, InwardInvoice, InvoiceType, ITC2BStatus
from app.models.gst import ReconciliationResult, ReconciliationStatus
from app.models.gst_return import GSTReturn, ReturnType, ReturnStatus
from app.models.user import User
from app.schemas.returns import GSTReturnOut
from app.api.deps import get_current_user
from app.services.gst_engine import check_itc_eligibility, compute_itc_setoff, get_compliance_calendar, get_return_due_date
from engine.gstr_compute import compute_mismatch as _engine_compute_mismatch, fy_periods as _engine_fy_periods
from engine.rules_loader import get_rules

router = APIRouter(prefix="/returns", tags=["returns"])


async def _get_business(db: AsyncSession, user: User) -> Business:
    business = await db.scalar(select(Business).where(Business.user_id == user.id))
    if not business:
        raise HTTPException(404, "Complete onboarding first.")
    return business


async def _get_or_none(db: AsyncSession, business_id: uuid.UUID, period: str, return_type: ReturnType) -> GSTReturn | None:
    return await db.scalar(
        select(GSTReturn).where(
            GSTReturn.business_id == business_id,
            GSTReturn.period == period,
            GSTReturn.return_type == return_type,
        )
    )


def _f(v) -> float:
    return float(v) if v else 0.0


# ─── GSTR-1 ──────────────────────────────────────────────────────────────────

@router.post("/gstr1/compute", response_model=GSTReturnOut)
async def compute_gstr1(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    invoices = (await db.scalars(
        select(OutwardInvoice).where(
            OutwardInvoice.business_id == business.id,
            OutwardInvoice.period == period,
        )
    )).all()

    def group(inv_type: InvoiceType):
        lst = [i for i in invoices if i.invoice_type == inv_type]
        return {
            "type": inv_type.value,
            "count": len(lst),
            "taxable_value": sum(_f(i.taxable_value) for i in lst),
            "igst": sum(_f(i.igst) for i in lst),
            "cgst": sum(_f(i.cgst) for i in lst),
            "sgst": sum(_f(i.sgst) for i in lst),
            "cess": sum(_f(i.cess) for i in lst),
        }

    b2b = group(InvoiceType.B2B)
    b2c_large = group(InvoiceType.B2C_LARGE)
    b2c_small = group(InvoiceType.B2C_SMALL)
    exports = group(InvoiceType.EXPORT)
    credit_notes = group(InvoiceType.CREDIT_NOTE)

    total_taxable = sum(_f(i.taxable_value) for i in invoices)
    total_igst = sum(_f(i.igst) for i in invoices)
    total_cgst = sum(_f(i.cgst) for i in invoices)
    total_sgst = sum(_f(i.sgst) for i in invoices)
    total_cess = sum(_f(i.cess) for i in invoices)
    total_tax = total_igst + total_cgst + total_sgst

    payload = {
        "b2b": [b2b],
        "b2c_large": [b2c_large],
        "b2c_small": [b2c_small],
        "exports": [exports],
        "credit_notes": [credit_notes],
        "summary": {
            "invoice_count": len(invoices),
            "total_taxable_value": total_taxable,
            "total_igst": total_igst,
            "total_cgst": total_cgst,
            "total_sgst": total_sgst,
            "total_cess": total_cess,
            "total_tax": total_tax,
        },
    }

    gstr1 = await _get_or_none(db, business.id, period, ReturnType.GSTR1)
    if gstr1:
        gstr1.computed_payload = payload
        gstr1.total_tax_payable = Decimal(str(total_tax))
        gstr1.status = ReturnStatus.DRAFT
    else:
        gstr1 = GSTReturn(
            id=uuid.uuid4(),
            business_id=business.id,
            period=period,
            return_type=ReturnType.GSTR1,
            computed_payload=payload,
            total_tax_payable=Decimal(str(total_tax)),
        )
        db.add(gstr1)

    await db.commit()
    await db.refresh(gstr1)
    return gstr1


@router.get("/gstr1", response_model=GSTReturnOut)
async def get_gstr1(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    gstr1 = await _get_or_none(db, business.id, period, ReturnType.GSTR1)
    if not gstr1:
        raise HTTPException(404, "GSTR-1 not computed for this period.")
    return gstr1


# ─── GSTR-3B ─────────────────────────────────────────────────────────────────

@router.post("/gstr3b/compute", response_model=GSTReturnOut)
async def compute_gstr3b(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)

    if business.is_composition:
        raise HTTPException(400, "Composition dealers file GSTR-4, not GSTR-3B.")

    outward = (await db.scalars(
        select(OutwardInvoice).where(
            OutwardInvoice.business_id == business.id,
            OutwardInvoice.period == period,
        )
    )).all()

    inward = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period == period,
        )
    )).all()

    recon_results = (await db.scalars(
        select(ReconciliationResult).where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.period == period,
        )
    )).all()
    reconciliation_done = len(recon_results) > 0

    # Determine if 2B lock has been applied for this period
    gstr2b_lock_applied = any(
        inv.itc_2b_status != ITC2BStatus.UNVERIFIED for inv in inward
    )

    out_igst = Decimal(str(sum(_f(i.igst) for i in outward)))
    out_cgst = Decimal(str(sum(_f(i.cgst) for i in outward)))
    out_sgst = Decimal(str(sum(_f(i.sgst) for i in outward)))
    out_cess = Decimal(str(sum(_f(getattr(i, "cess", 0)) for i in outward)))
    out_total = out_igst + out_cgst + out_sgst + out_cess

    itc_igst = itc_cgst = itc_sgst = Decimal("0")
    blocked_count = 0
    expired_count = 0
    missing_2b_count = 0

    for inv in inward:
        # If 2B lock applied: skip invoices missing from 2B (unless user accepted risk)
        if gstr2b_lock_applied and inv.itc_2b_status == ITC2BStatus.MISSING_IN_2B:
            missing_2b_count += 1
            blocked_count += 1
            continue

        # Skip unverified invoices when 2B lock is active (conservative)
        if gstr2b_lock_applied and inv.itc_2b_status == ITC2BStatus.UNVERIFIED:
            missing_2b_count += 1
            continue

        # Standard eligibility check (Section 16(4) time-bar + Section 17(5) blocks)
        if reconciliation_done or gstr2b_lock_applied:
            result = check_itc_eligibility(
                invoice_id=str(inv.id),
                supplier_name=inv.supplier_name,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                igst=inv.igst,
                cgst=inv.cgst,
                sgst=inv.sgst,
                itc_category=inv.itc_blocked_reason,
                is_rcm=inv.is_rcm,
            )
            if result.is_eligible:
                itc_igst += result.igst
                itc_cgst += result.cgst
                itc_sgst += result.sgst
            else:
                reason_lower = result.blocked_reason.lower()
                if "lapsed" in reason_lower or "time" in reason_lower or "expir" in reason_lower:
                    expired_count += 1
                else:
                    blocked_count += 1

    itc_total = itc_igst + itc_cgst + itc_sgst

    setoff = compute_itc_setoff(itc_igst, itc_cgst, itc_sgst, out_igst, out_cgst, out_sgst)

    net_total = setoff.total_cash_required + max(out_cess, Decimal("0"))

    payload = {
        "outward_tax_liability": {
            "igst": float(out_igst), "cgst": float(out_cgst),
            "sgst": float(out_sgst), "cess": float(out_cess), "total": float(out_total),
        },
        "itc_available": {
            "igst": float(itc_igst), "cgst": float(itc_cgst),
            "sgst": float(itc_sgst), "cess": 0.0, "total": float(itc_total),
        },
        "itc_setoff": {
            "igst_credit_used": float(setoff.igst_credit_used),
            "cgst_credit_used": float(setoff.cgst_credit_used),
            "sgst_credit_used": float(setoff.sgst_credit_used),
            "igst_cash_required": float(setoff.igst_cash_required),
            "cgst_cash_required": float(setoff.cgst_cash_required),
            "sgst_cash_required": float(setoff.sgst_cash_required),
        },
        "net_cash_payable": {
            "igst": float(setoff.igst_cash_required),
            "cgst": float(setoff.cgst_cash_required),
            "sgst": float(setoff.sgst_cash_required),
            "cess": float(out_cess),
            "total": float(net_total),
        },
        "itc_blocked_count": blocked_count,
        "itc_expired_count": expired_count,
        "itc_missing_2b_count": missing_2b_count,
        "gstr2b_lock_applied": gstr2b_lock_applied,
        "reconciliation_done": reconciliation_done,
        "invoice_count": len(outward),
    }

    gstr3b = await _get_or_none(db, business.id, period, ReturnType.GSTR3B)
    if gstr3b:
        gstr3b.computed_payload = payload
        gstr3b.total_tax_payable = net_total
        gstr3b.itc_claimed = itc_total
        gstr3b.status = ReturnStatus.DRAFT
    else:
        gstr3b = GSTReturn(
            id=uuid.uuid4(),
            business_id=business.id,
            period=period,
            return_type=ReturnType.GSTR3B,
            computed_payload=payload,
            total_tax_payable=net_total,
            itc_claimed=itc_total,
        )
        db.add(gstr3b)

    await db.commit()
    await db.refresh(gstr3b)
    return gstr3b


@router.get("/gstr3b", response_model=GSTReturnOut)
async def get_gstr3b(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    gstr3b = await _get_or_none(db, business.id, period, ReturnType.GSTR3B)
    if not gstr3b:
        raise HTTPException(404, "GSTR-3B not computed.")
    return gstr3b


# ─── GSTR-4 (Composition Dealers) ────────────────────────────────────────────

@router.post("/gstr4/compute", response_model=GSTReturnOut)
async def compute_gstr4(
    period: str = Query(..., description="Quarter period e.g. 2025-01 (Jan quarter = Oct-Dec)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)

    if not business.is_composition:
        raise HTTPException(400, "Only composition dealers file GSTR-4.")

    # Rate loaded from rules — respects business_type (fixes old hardcoded 1% bug)
    rules = get_rules()
    business_type = getattr(business, "composition_type", "trader") or "trader"
    rate_pct = rules.composition_rates.get(business_type, rules.composition_rates.get("trader", Decimal("1.0")))
    COMPOSITION_RATE = rate_pct / 100

    outward = (await db.scalars(
        select(OutwardInvoice).where(
            OutwardInvoice.business_id == business.id,
            OutwardInvoice.period == period,
        )
    )).all()

    inward = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period == period,
        )
    )).all()

    total_taxable = Decimal(str(sum(_f(i.taxable_value) for i in outward)))
    composition_tax = (total_taxable * COMPOSITION_RATE).quantize(Decimal("0.01"))
    cgst_payable = (composition_tax / 2).quantize(Decimal("0.01"))
    sgst_payable = composition_tax - cgst_payable

    # RCM on inward — composition dealers pay GST on RCM purchases at normal rates
    rcm_invoices = [i for i in inward if i.is_rcm]
    rcm_igst = Decimal(str(sum(_f(i.igst) for i in rcm_invoices)))
    rcm_cgst = Decimal(str(sum(_f(i.cgst) for i in rcm_invoices)))
    rcm_sgst = Decimal(str(sum(_f(i.sgst) for i in rcm_invoices)))
    rcm_total = rcm_igst + rcm_cgst + rcm_sgst

    total_payable = composition_tax + rcm_total

    payload = {
        "aggregate_turnover": float(total_taxable),
        "composition_tax_rate_pct": float(rate_pct),
        "composition_tax_rate": float(COMPOSITION_RATE),
        "composition_tax": float(composition_tax),
        "cgst_payable": float(cgst_payable),
        "sgst_payable": float(sgst_payable),
        "rcm_liability": {
            "igst": float(rcm_igst), "cgst": float(rcm_cgst),
            "sgst": float(rcm_sgst), "total": float(rcm_total),
            "invoice_count": len(rcm_invoices),
        },
        "total_tax_payable": float(total_payable),
        "note": "Composition dealers cannot claim ITC. Tax charged on turnover at flat rate.",
        "invoice_count": len(outward),
    }

    gstr4 = await _get_or_none(db, business.id, period, ReturnType.GSTR4)
    if gstr4:
        gstr4.computed_payload = payload
        gstr4.total_tax_payable = total_payable
        gstr4.itc_claimed = Decimal("0")
        gstr4.status = ReturnStatus.DRAFT
    else:
        gstr4 = GSTReturn(
            id=uuid.uuid4(),
            business_id=business.id,
            period=period,
            return_type=ReturnType.GSTR4,
            computed_payload=payload,
            total_tax_payable=total_payable,
            itc_claimed=Decimal("0"),
        )
        db.add(gstr4)

    await db.commit()
    await db.refresh(gstr4)
    return gstr4


@router.get("/gstr4", response_model=GSTReturnOut)
async def get_gstr4(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    gstr4 = await _get_or_none(db, business.id, period, ReturnType.GSTR4)
    if not gstr4:
        raise HTTPException(404, "GSTR-4 not computed.")
    return gstr4



# ─── GSTR-9 (Annual Return) ──────────────────────────────────────────────────

def _fy_periods(fy: str) -> list[str]:
    return _engine_fy_periods(fy)


@router.post("/gstr9/compute", response_model=GSTReturnOut)
async def compute_gstr9(
    fy: str = Query(..., description="Financial year e.g. 2024-25"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    if business.is_composition:
        raise HTTPException(400, "Composition dealers file GSTR-4 annually, not GSTR-9.")

    periods = _fy_periods(fy)

    outward = (await db.scalars(
        select(OutwardInvoice).where(
            OutwardInvoice.business_id == business.id,
            OutwardInvoice.period.in_(periods),
        )
    )).all()

    inward = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period.in_(periods),
        )
    )).all()

    gstr1_returns = (await db.scalars(
        select(GSTReturn).where(
            GSTReturn.business_id == business.id,
            GSTReturn.period.in_(periods),
            GSTReturn.return_type == ReturnType.GSTR1,
        )
    )).all()

    gstr3b_returns = (await db.scalars(
        select(GSTReturn).where(
            GSTReturn.business_id == business.id,
            GSTReturn.period.in_(periods),
            GSTReturn.return_type == ReturnType.GSTR3B,
        )
    )).all()

    total_taxable = sum(_f(i.taxable_value) for i in outward)
    total_igst_out = sum(_f(i.igst) for i in outward)
    total_cgst_out = sum(_f(i.cgst) for i in outward)
    total_sgst_out = sum(_f(i.sgst) for i in outward)
    total_cess_out = sum(_f(getattr(i, "cess", 0)) for i in outward)
    total_tax_out = total_igst_out + total_cgst_out + total_sgst_out + total_cess_out

    total_igst_in = sum(_f(i.igst) for i in inward)
    total_cgst_in = sum(_f(i.cgst) for i in inward)
    total_sgst_in = sum(_f(i.sgst) for i in inward)
    total_itc = total_igst_in + total_cgst_in + total_sgst_in

    gstr3b_tax_paid = sum(_f(r.total_tax_payable) for r in gstr3b_returns)
    gstr3b_itc_claimed = sum(_f(r.itc_claimed) for r in gstr3b_returns)

    by_type = {}
    for inv_type in InvoiceType:
        lst = [i for i in outward if i.invoice_type == inv_type]
        by_type[inv_type.value] = {
            "count": len(lst),
            "taxable_value": sum(_f(i.taxable_value) for i in lst),
            "igst": sum(_f(i.igst) for i in lst),
            "cgst": sum(_f(i.cgst) for i in lst),
            "sgst": sum(_f(i.sgst) for i in lst),
        }

    period_wise = {}
    for p in periods:
        p_out = [i for i in outward if i.period == p]
        p_in = [i for i in inward if i.period == p]
        gstr1 = next((r for r in gstr1_returns if r.period == p), None)
        gstr3b = next((r for r in gstr3b_returns if r.period == p), None)
        period_wise[p] = {
            "outward_count": len(p_out),
            "outward_taxable": sum(_f(i.taxable_value) for i in p_out),
            "outward_tax": sum(_f(i.igst) + _f(i.cgst) + _f(i.sgst) for i in p_out),
            "inward_count": len(p_in),
            "inward_itc": sum(_f(i.igst) + _f(i.cgst) + _f(i.sgst) for i in p_in),
            "gstr1_filed": gstr1.status == ReturnStatus.FILED if gstr1 else False,
            "gstr3b_filed": gstr3b.status == ReturnStatus.FILED if gstr3b else False,
            "tax_paid": _f(gstr3b.total_tax_payable) if gstr3b else 0,
        }

    payload = {
        "financial_year": fy,
        "periods": periods,
        "outward_supplies": {
            "by_type": by_type,
            "total_taxable_value": total_taxable,
            "total_igst": total_igst_out,
            "total_cgst": total_cgst_out,
            "total_sgst": total_sgst_out,
            "total_cess": total_cess_out,
            "total_tax": total_tax_out,
            "invoice_count": len(outward),
        },
        "inward_supplies": {
            "total_igst": total_igst_in,
            "total_cgst": total_cgst_in,
            "total_sgst": total_sgst_in,
            "total_itc": total_itc,
            "invoice_count": len(inward),
        },
        "returns_summary": {
            "gstr1_filed_count": sum(1 for r in gstr1_returns if r.status == ReturnStatus.FILED),
            "gstr3b_filed_count": sum(1 for r in gstr3b_returns if r.status == ReturnStatus.FILED),
            "gstr1_total": len(gstr1_returns),
            "gstr3b_total": len(gstr3b_returns),
            "tax_paid_via_gstr3b": gstr3b_tax_paid,
            "itc_claimed_via_gstr3b": gstr3b_itc_claimed,
        },
        "period_wise": period_wise,
    }

    existing = await _get_or_none(db, business.id, fy, ReturnType.GSTR9)
    if existing:
        existing.computed_payload = payload
        existing.total_tax_payable = Decimal(str(gstr3b_tax_paid))
        existing.itc_claimed = Decimal(str(gstr3b_itc_claimed))
        existing.status = ReturnStatus.DRAFT
    else:
        existing = GSTReturn(
            id=uuid.uuid4(),
            business_id=business.id,
            period=fy,
            return_type=ReturnType.GSTR9,
            computed_payload=payload,
            total_tax_payable=Decimal(str(gstr3b_tax_paid)),
            itc_claimed=Decimal(str(gstr3b_itc_claimed)),
        )
        db.add(existing)

    await db.commit()
    await db.refresh(existing)
    return existing


@router.get("/gstr9", response_model=GSTReturnOut)
async def get_gstr9(
    fy: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    gstr9 = await _get_or_none(db, business.id, fy, ReturnType.GSTR9)
    if not gstr9:
        raise HTTPException(404, "GSTR-9 not computed.")
    return gstr9


@router.get("/trends")
async def get_trends(
    periods: str = Query(..., description="Comma-separated periods e.g. 2025-01,2025-02"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    period_list = [p.strip() for p in periods.split(",")]

    outward = (await db.scalars(
        select(OutwardInvoice).where(
            OutwardInvoice.business_id == business.id,
            OutwardInvoice.period.in_(period_list),
        )
    )).all()

    inward = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period.in_(period_list),
        )
    )).all()

    gstr3b_returns = (await db.scalars(
        select(GSTReturn).where(
            GSTReturn.business_id == business.id,
            GSTReturn.period.in_(period_list),
            GSTReturn.return_type == ReturnType.GSTR3B,
        )
    )).all()

    result = []
    for p in period_list:
        p_out = [i for i in outward if i.period == p]
        p_in = [i for i in inward if i.period == p]
        gstr3b = next((r for r in gstr3b_returns if r.period == p), None)
        result.append({
            "period": p,
            "taxable_value": sum(_f(i.taxable_value) for i in p_out),
            "tax_liability": sum(_f(i.igst) + _f(i.cgst) + _f(i.sgst) for i in p_out),
            "itc_available": sum(_f(i.igst) + _f(i.cgst) + _f(i.sgst) for i in p_in),
            "tax_paid": _f(gstr3b.total_tax_payable) if gstr3b else 0,
            "itc_claimed": _f(gstr3b.itc_claimed) if gstr3b else 0,
            "invoice_count": len(p_out),
        })

    return result


@router.post("/{return_id}/file", response_model=GSTReturnOut)
async def file_return(
    return_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    gst_return = await db.get(GSTReturn, uuid.UUID(return_id))
    if not gst_return or gst_return.business_id != business.id:
        raise HTTPException(404, "Return not found")
    if gst_return.status == ReturnStatus.FILED:
        raise HTTPException(409, "Return already filed")

    # Sequencer: block GSTR-3B filing if GSTR-1 not filed for same period
    if gst_return.return_type == ReturnType.GSTR3B:
        gstr1 = await _get_or_none(db, business.id, gst_return.period, ReturnType.GSTR1)
        if not gstr1 or gstr1.status != ReturnStatus.FILED:
            raise HTTPException(
                422,
                f"GSTR-1 for {gst_return.period} must be filed before GSTR-3B. "
                "File GSTR-1 first to maintain outward supply consistency."
            )
        # Block if mismatch unresolved
        mismatch = _compute_mismatch(gstr1, gst_return)
        if mismatch["has_mismatch"]:
            raise HTTPException(
                422,
                f"GSTR-1 vs GSTR-3B outward tax mismatch exceeds 1% threshold "
                f"(delta ₹{mismatch['total_tax_delta']:.2f}). "
                "Recompute GSTR-3B or correct invoices before filing."
            )

    # Sequencer: block GSTR-9 filing if any monthly GSTR-3B not filed
    if gst_return.return_type == ReturnType.GSTR9:
        fy = gst_return.period
        periods = _fy_periods(fy)
        unfiled = []
        for p in periods:
            r = await _get_or_none(db, business.id, p, ReturnType.GSTR3B)
            if not r or r.status != ReturnStatus.FILED:
                unfiled.append(p)
        if unfiled:
            raise HTTPException(
                422,
                f"GSTR-3B not filed for periods: {', '.join(unfiled)}. "
                "File all 12 monthly returns before submitting GSTR-9."
            )

    await asyncio.sleep(2)

    suffix = "".join(random.choices(string.digits + string.ascii_uppercase, k=6))
    period_compact = gst_return.period.replace("-", "")
    gst_return.arn = f"AA{business.state_code}{period_compact}{suffix}"
    gst_return.status = ReturnStatus.FILED
    gst_return.filed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(gst_return)
    return gst_return


# ─── Mismatch Helper ─────────────────────────────────────────────────────────

def _compute_mismatch(gstr1: GSTReturn, gstr3b: GSTReturn) -> dict[str, Any]:
    """Delegate to engine.gstr_compute.compute_mismatch."""
    return _engine_compute_mismatch(
        gstr1.computed_payload or {},
        gstr3b.computed_payload or {},
    )


# ─── Mismatch Report Endpoint ─────────────────────────────────────────────────

@router.get("/mismatch-report")
async def get_mismatch_report(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Compare GSTR-1 and GSTR-3B outward tax figures for a period.
    GSTN's ANSR system auto-flags divergence > 1% — catch it here first.
    """
    business = await _get_business(db, current_user)
    gstr1 = await _get_or_none(db, business.id, period, ReturnType.GSTR1)
    gstr3b = await _get_or_none(db, business.id, period, ReturnType.GSTR3B)

    if not gstr1:
        raise HTTPException(404, f"GSTR-1 not computed for {period}. Run compute first.")
    if not gstr3b:
        raise HTTPException(404, f"GSTR-3B not computed for {period}. Run compute first.")

    mismatch = _compute_mismatch(gstr1, gstr3b)
    return {
        "period": period,
        "gstr1_status": gstr1.status.value,
        "gstr3b_status": gstr3b.status.value,
        **mismatch,
        "risk": (
            "HIGH — GSTN ANSR system will flag this. Correct before filing."
            if mismatch["has_mismatch"]
            else "OK — within 1% tolerance."
        ),
    }


# ─── Compliance Status Dashboard ─────────────────────────────────────────────

@router.get("/compliance-status")
async def get_compliance_status(
    period: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Full compliance dependency tree for a period:
    - GSTR-1 status + due date
    - GSTR-3B status + due date + blocking issues
    - Mismatch flag
    - ITC reconciliation status
    """
    from datetime import date
    business = await _get_business(db, current_user)

    gstr1 = await _get_or_none(db, business.id, period, ReturnType.GSTR1)
    gstr3b = await _get_or_none(db, business.id, period, ReturnType.GSTR3B)

    calendar = get_compliance_calendar(period, business.is_composition)
    due_map = {d.return_type: d for d in calendar}

    gstr1_due = due_map.get("GSTR-1")
    gstr3b_due = due_map.get("GSTR-3B")

    blockers: list[str] = []

    if not gstr1 or gstr1.status != ReturnStatus.FILED:
        blockers.append("GSTR-1 not filed — required before GSTR-3B filing")

    mismatch_info = None
    if gstr1 and gstr3b:
        mismatch_info = _compute_mismatch(gstr1, gstr3b)
        if mismatch_info["has_mismatch"]:
            blockers.append(
                f"GSTR-1 vs GSTR-3B mismatch: ₹{mismatch_info['total_tax_delta']:.2f} "
                f"({mismatch_info['delta_pct']:.2f}%)"
            )

    recon_results = (await db.scalars(
        select(ReconciliationResult).where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.period == period,
        )
    )).all()
    unresolved_recon = sum(1 for r in recon_results if not r.resolved)
    if unresolved_recon > 0:
        blockers.append(f"{unresolved_recon} unresolved 2B reconciliation mismatches — ITC at risk")

    return {
        "period": period,
        "business_gstin": business.gstin,
        "is_composition": business.is_composition,
        "returns": {
            "gstr1": {
                "status": gstr1.status.value if gstr1 else "not_computed",
                "due_date": gstr1_due.due_date.isoformat() if gstr1_due else None,
                "days_remaining": gstr1_due.days_remaining if gstr1_due else None,
                "is_overdue": gstr1_due.is_overdue if gstr1_due else None,
                "arn": gstr1.arn if gstr1 else None,
            },
            "gstr3b": {
                "status": gstr3b.status.value if gstr3b else "not_computed",
                "due_date": gstr3b_due.due_date.isoformat() if gstr3b_due else None,
                "days_remaining": gstr3b_due.days_remaining if gstr3b_due else None,
                "is_overdue": gstr3b_due.is_overdue if gstr3b_due else None,
                "arn": gstr3b.arn if gstr3b else None,
            },
        },
        "mismatch": mismatch_info,
        "recon_summary": {
            "total_results": len(recon_results),
            "unresolved": unresolved_recon,
        },
        "blockers": blockers,
        "ready_to_file_gstr3b": len(blockers) == 0,
    }


# ─── GSTR-2B Hard-Lock ────────────────────────────────────────────────────────

@router.post("/gstr2b-lock")
async def apply_gstr2b_lock(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Section 16(2)(aa): run 2B reconciliation and stamp each inward invoice
    with its itc_2b_status. After this, GSTR-3B compute will only claim ITC
    for MATCHED or ACCEPTED_WITH_RISK invoices.

    Matching logic: match by supplier_gstin + invoice_number.
    Real production use would match against actual GSTN 2B API data.
    Here we match against GSTR2BRecord rows already imported for the period.
    """
    from app.models.gst import GSTR2BRecord
    business = await _get_business(db, current_user)

    inward = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period == period,
        )
    )).all()

    gstr2b_records = (await db.scalars(
        select(GSTR2BRecord).where(
            GSTR2BRecord.user_id == current_user.id,
            GSTR2BRecord.period == period,
        )
    )).all()

    # Build lookup: (supplier_gstin_upper, invoice_number_upper) → True
    gstr2b_index: set[tuple[str, str]] = {
        (r.supplier_gstin.upper(), r.invoice_number.upper())
        for r in gstr2b_records
    }

    matched = missing = already_locked = 0

    for inv in inward:
        if inv.itc_2b_status == ITC2BStatus.ACCEPTED_WITH_RISK:
            already_locked += 1
            continue

        gstin_key = (inv.supplier_gstin or "").upper()
        inv_key = inv.invoice_number.upper()

        if (gstin_key, inv_key) in gstr2b_index:
            inv.itc_2b_status = ITC2BStatus.MATCHED
            matched += 1
        else:
            # No GSTIN invoices (URD / composition) can't appear in 2B — treat as risk
            if not inv.supplier_gstin:
                inv.itc_2b_status = ITC2BStatus.ACCEPTED_WITH_RISK
                already_locked += 1
            else:
                inv.itc_2b_status = ITC2BStatus.MISSING_IN_2B
                missing += 1

    await db.commit()

    return {
        "period": period,
        "total_invoices": len(inward),
        "matched": matched,
        "missing_in_2b": missing,
        "accepted_with_risk": already_locked,
        "gstr2b_records_available": len(gstr2b_records),
        "message": (
            f"{missing} invoices missing from GSTR-2B — ITC of these will be blocked in GSTR-3B. "
            "Use POST /returns/gstr2b-accept-risk/{invoice_id} to override with risk acknowledgement."
            if missing > 0
            else "All invoices matched in GSTR-2B. ITC fully claimable."
        ),
    }


@router.post("/gstr2b-accept-risk/{invoice_id}")
async def accept_2b_risk(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Override 2B lock for a specific invoice.
    User explicitly acknowledges ITC risk under Section 16(2)(aa).
    GSTN may raise a demand — this is an informed business decision.
    """
    business = await _get_business(db, current_user)
    inv = await db.get(InwardInvoice, uuid.UUID(invoice_id))
    if not inv or inv.business_id != business.id:
        raise HTTPException(404, "Invoice not found")
    if inv.itc_2b_status != ITC2BStatus.MISSING_IN_2B:
        raise HTTPException(400, f"Invoice status is '{inv.itc_2b_status.value}' — only MISSING_IN_2B invoices can be risk-accepted")

    inv.itc_2b_status = ITC2BStatus.ACCEPTED_WITH_RISK
    await db.commit()
    return {
        "invoice_id": invoice_id,
        "new_status": ITC2BStatus.ACCEPTED_WITH_RISK.value,
        "warning": (
            "ITC claimed without 2B match. Supplier GSTN may issue demand under Section 73/74 "
            "if supplier fails to file GSTR-1. Ensure supplier files before next recon."
        ),
    }
