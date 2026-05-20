from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from decimal import Decimal
from app.core.database import get_db
from app.models.gst import GSTR2BRecord, ReconciliationResult, ReconciliationStatus, IMSAction
from app.models.invoice import InwardInvoice
from app.models.business import Business
from app.schemas.gst import ReconciliationResultOut, ReconciliationSummary, GSTR2BRecordOut
from app.services.fuzzy_match import find_best_match
from app.api.deps import get_current_user
from app.models.user import User
import uuid

router = APIRouter(prefix="/gst", tags=["gst"])


async def _get_business(db: AsyncSession, user: User) -> Business:
    business = await db.scalar(select(Business).where(Business.user_id == user.id))
    if not business:
        raise HTTPException(404, "Complete onboarding first.")
    return business


@router.get("/gstr2b", response_model=list[GSTR2BRecordOut])
async def list_gstr2b(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = await db.scalars(
        select(GSTR2BRecord)
        .where(GSTR2BRecord.user_id == current_user.id, GSTR2BRecord.period == period)
        .order_by(GSTR2BRecord.supplier_name)
    )
    return records.all()


@router.put("/ims/{record_id}")
async def update_ims_action(
    record_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await db.get(GSTR2BRecord, uuid.UUID(record_id))
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Record not found")
    action_str = body.get("action", "pending")
    record.ims_action = IMSAction(action_str)
    await db.commit()
    return {"status": "updated", "action": action_str}


@router.post("/reconciliation/run")
async def run_reconciliation(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)

    # Delete old results for this period before re-running
    await db.execute(
        delete(ReconciliationResult).where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.period == period,
        )
    )

    gstr2b_records = (await db.scalars(
        select(GSTR2BRecord).where(
            GSTR2BRecord.user_id == current_user.id,
            GSTR2BRecord.period == period,
        )
    )).all()

    inward_records = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period == period,
        )
    )).all()

    matched = 0

    for g2b in gstr2b_records:
        candidates = [
            {"gstin": p.supplier_gstin, "name": p.supplier_name, "id": str(p.id)}
            for p in inward_records
        ]
        best_match, result = find_best_match(
            {"gstin": g2b.supplier_gstin, "name": g2b.supplier_name},
            candidates,
        )

        if best_match and result.confidence >= 90:
            matched += 1
            recon = ReconciliationResult(
                user_id=current_user.id,
                period=period,
                gstr2b_id=g2b.id,
                inward_invoice_id=uuid.UUID(best_match["id"]),
                status=ReconciliationStatus.MATCHED,
                match_confidence=result.confidence,
            )
        else:
            recon = ReconciliationResult(
                user_id=current_user.id,
                period=period,
                gstr2b_id=g2b.id,
                status=ReconciliationStatus.MISSING_IN_BOOKS,
                match_confidence=result.confidence,
            )
        db.add(recon)

    # InwardInvoices not matched by any GSTR-2B → MISSING_IN_2B
    matched_inward_ids = set()
    for g2b in gstr2b_records:
        candidates = [
            {"gstin": p.supplier_gstin, "name": p.supplier_name, "id": str(p.id)}
            for p in inward_records
        ]
        best_match, result = find_best_match(
            {"gstin": g2b.supplier_gstin, "name": g2b.supplier_name},
            candidates,
        )
        if best_match and result.confidence >= 90:
            matched_inward_ids.add(best_match["id"])

    for inv in inward_records:
        if str(inv.id) not in matched_inward_ids:
            db.add(ReconciliationResult(
                user_id=current_user.id,
                period=period,
                inward_invoice_id=inv.id,
                status=ReconciliationStatus.MISSING_IN_2B,
                match_confidence=0,
            ))

    await db.commit()
    return {"period": period, "matched": matched, "total_gstr2b": len(gstr2b_records)}


@router.get("/reconciliation/results")
async def get_reconciliation_results(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (await db.scalars(
        select(ReconciliationResult).where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.period == period,
        ).order_by(ReconciliationResult.status)
    )).all()

    # Enrich with supplier/invoice data from GSTR-2B or InwardInvoice
    rows = []
    for r in results:
        row: dict = {
            "id": str(r.id),
            "period": r.period,
            "status": r.status.value,
            "match_confidence": r.match_confidence,
            "ims_action": None,
            "supplier_name": "",
            "supplier_gstin": None,
            "invoice_number": "",
            "invoice_date": "",
            "taxable_value": "0",
            "igst": "0",
            "cgst": "0",
            "sgst": "0",
        }

        if r.gstr2b_id:
            g2b = await db.get(GSTR2BRecord, r.gstr2b_id)
            if g2b:
                row["supplier_name"] = g2b.supplier_name
                row["supplier_gstin"] = g2b.supplier_gstin
                row["invoice_number"] = g2b.invoice_number
                row["invoice_date"] = str(g2b.invoice_date)
                row["taxable_value"] = str(g2b.taxable_value)
                row["igst"] = str(g2b.igst)
                row["cgst"] = str(g2b.cgst)
                row["sgst"] = str(g2b.sgst)
                row["ims_action"] = g2b.ims_action.value if g2b.ims_action else None

        elif r.inward_invoice_id:
            inv = await db.get(InwardInvoice, r.inward_invoice_id)
            if inv:
                row["supplier_name"] = inv.supplier_name
                row["supplier_gstin"] = inv.supplier_gstin
                row["invoice_number"] = inv.invoice_number
                row["invoice_date"] = str(inv.invoice_date)
                row["taxable_value"] = str(inv.taxable_value)
                row["igst"] = str(inv.igst)
                row["cgst"] = str(inv.cgst)
                row["sgst"] = str(inv.sgst)

        rows.append(row)

    return rows


@router.get("/reconciliation/summary", response_model=ReconciliationSummary)
async def get_reconciliation_summary(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (await db.scalars(
        select(ReconciliationResult).where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.period == period,
        )
    )).all()

    status_counts = {s: 0 for s in ReconciliationStatus}
    for r in results:
        status_counts[r.status] += 1

    return ReconciliationSummary(
        period=period,
        total_records=len(results),
        matched=status_counts[ReconciliationStatus.MATCHED],
        missing_in_2b=status_counts[ReconciliationStatus.MISSING_IN_2B],
        missing_in_books=status_counts[ReconciliationStatus.MISSING_IN_BOOKS],
        amount_mismatch=status_counts[ReconciliationStatus.AMOUNT_MISMATCH],
        pending_ims=status_counts[ReconciliationStatus.PENDING_IMS],
        total_itc_eligible=Decimal("0"),
        total_itc_at_risk=Decimal("0"),
    )


@router.get("/filed-periods")
async def get_filed_periods(
    current_user: User = Depends(get_current_user),
):
    """Mock GSP API: returns periods for which GST returns have been filed."""
    from datetime import date
    today = date.today()
    periods = []
    for i in range(1, 13):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        periods.append({
            "period": f"{year}-{month:02d}",
            "gstr1_status": "filed" if i <= 6 else "not_filed",
            "gstr3b_status": "filed" if i <= 5 else "not_filed",
        })
    return {"periods": periods, "source": "mock_gsp"}
