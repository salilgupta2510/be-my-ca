import asyncio
import random
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.business import Business
from app.models.invoice import OutwardInvoice, InwardInvoice, InvoiceType
from app.models.gst import ReconciliationResult, ReconciliationStatus
from app.models.gst_return import GSTReturn, ReturnType, ReturnStatus
from app.models.user import User
from app.schemas.returns import GSTReturnOut
from app.api.deps import get_current_user
from app.services.gst_engine import check_itc_eligibility, compute_itc_setoff

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

    matched_recon = (await db.scalars(
        select(ReconciliationResult).where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.period == period,
            ReconciliationResult.status == ReconciliationStatus.MATCHED,
        )
    )).all()
    reconciliation_done = len(matched_recon) > 0

    out_igst = Decimal(str(sum(_f(i.igst) for i in outward)))
    out_cgst = Decimal(str(sum(_f(i.cgst) for i in outward)))
    out_sgst = Decimal(str(sum(_f(i.sgst) for i in outward)))
    out_cess = Decimal(str(sum(_f(getattr(i, "cess", 0)) for i in outward)))
    out_total = out_igst + out_cgst + out_sgst + out_cess

    itc_igst = itc_cgst = itc_sgst = Decimal("0")
    blocked_count = 0
    expired_count = 0

    if reconciliation_done:
        for inv in inward:
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
                if "expired" in result.blocked_reason.lower() or "time limit" in result.blocked_reason.lower():
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

    # Composition rate: 1% for traders (0.5% CGST + 0.5% SGST)
    # 2.5% for manufacturers, 5% for restaurants — default to 1%
    COMPOSITION_RATE = Decimal("0.01")

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

    await asyncio.sleep(2)

    suffix = "".join(random.choices(string.digits + string.ascii_uppercase, k=6))
    period_compact = gst_return.period.replace("-", "")
    gst_return.arn = f"AA{business.state_code}{period_compact}{suffix}"
    gst_return.status = ReturnStatus.FILED
    gst_return.filed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(gst_return)
    return gst_return
