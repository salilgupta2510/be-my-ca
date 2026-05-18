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

    out_igst = sum(_f(i.igst) for i in outward)
    out_cgst = sum(_f(i.cgst) for i in outward)
    out_sgst = sum(_f(i.sgst) for i in outward)
    out_total = out_igst + out_cgst + out_sgst

    if reconciliation_done:
        itc_igst = sum(_f(i.igst) for i in inward)
        itc_cgst = sum(_f(i.cgst) for i in inward)
        itc_sgst = sum(_f(i.sgst) for i in inward)
    else:
        itc_igst = itc_cgst = itc_sgst = 0.0
    itc_total = itc_igst + itc_cgst + itc_sgst

    net_igst = max(out_igst - itc_igst, 0.0)
    net_cgst = max(out_cgst - itc_cgst, 0.0)
    net_sgst = max(out_sgst - itc_sgst, 0.0)
    net_total = net_igst + net_cgst + net_sgst

    payload = {
        "outward_tax_liability": {"igst": out_igst, "cgst": out_cgst, "sgst": out_sgst, "cess": 0.0, "total": out_total},
        "itc_available": {"igst": itc_igst, "cgst": itc_cgst, "sgst": itc_sgst, "cess": 0.0, "total": itc_total},
        "net_tax_payable": {"igst": net_igst, "cgst": net_cgst, "sgst": net_sgst, "cess": 0.0, "total": net_total},
        "reconciliation_done": reconciliation_done,
        "invoice_count": len(outward),
    }

    gstr3b = await _get_or_none(db, business.id, period, ReturnType.GSTR3B)
    if gstr3b:
        gstr3b.computed_payload = payload
        gstr3b.total_tax_payable = Decimal(str(net_total))
        gstr3b.itc_claimed = Decimal(str(itc_total))
        gstr3b.status = ReturnStatus.DRAFT
    else:
        gstr3b = GSTReturn(
            id=uuid.uuid4(),
            business_id=business.id,
            period=period,
            return_type=ReturnType.GSTR3B,
            computed_payload=payload,
            total_tax_payable=Decimal(str(net_total)),
            itc_claimed=Decimal(str(itc_total)),
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
