from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.business import Business
from app.models.invoice import InwardInvoice
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.compliance import (
    GSTINValidationOut,
    DueDateOut,
    LateFeeOut,
    AggregateTurnoverOut,
    ITCEligibilitySummaryOut,
    ITCEligibilityItemOut,
    ITCSetoffOut,
)
from app.services.gst_engine import (
    validate_gstin,
    get_state_from_gstin,
    get_state_name,
    get_compliance_calendar,
    compute_late_fee,
    compute_aggregate_turnover,
    check_itc_eligibility,
    compute_itc_setoff,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


async def _get_business(db: AsyncSession, user: User) -> Business:
    business = await db.scalar(select(Business).where(Business.user_id == user.id))
    if not business:
        raise HTTPException(404, "Complete onboarding first.")
    return business


@router.get("/validate-gstin", response_model=GSTINValidationOut)
async def validate_gstin_endpoint(gstin: str = Query(..., min_length=15, max_length=15)):
    is_valid, error = validate_gstin(gstin)
    state_code = get_state_from_gstin(gstin) if is_valid else None
    state_name = get_state_name(state_code) if state_code else None
    pan = gstin[2:12] if is_valid else None
    return GSTINValidationOut(
        gstin=gstin.upper(),
        is_valid=is_valid,
        error=error if not is_valid else None,
        state_code=state_code,
        state_name=state_name,
        pan=pan,
    )


@router.get("/due-dates", response_model=list[DueDateOut])
async def get_due_dates(
    period: str = Query(..., examples=["2025-01"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    calendar = get_compliance_calendar(period, business.is_composition)
    return [
        DueDateOut(
            return_type=d.return_type,
            period=d.period,
            due_date=d.due_date,
            days_remaining=d.days_remaining,
            is_overdue=d.is_overdue,
            late_fee_applicable=d.late_fee_applicable,
        )
        for d in calendar
    ]


@router.get("/late-fees", response_model=LateFeeOut)
async def get_late_fees(
    return_type: str = Query(...),
    period: str = Query(...),
    filing_date: date = Query(...),
    is_nil_return: bool = Query(False),
    annual_turnover: Decimal = Query(Decimal("0")),
    current_user: User = Depends(get_current_user),
):
    result = compute_late_fee(return_type, period, filing_date, is_nil_return, annual_turnover)
    return LateFeeOut(
        return_type=result.return_type,
        period=result.period,
        due_date=result.due_date,
        filing_date=result.filing_date,
        days_late=result.days_late,
        late_fee_cgst=result.late_fee_cgst,
        late_fee_sgst=result.late_fee_sgst,
        late_fee_total=result.late_fee_total,
        max_cap=result.max_cap,
        is_nil_return=result.is_nil_return,
    )


@router.get("/aggregate-turnover", response_model=AggregateTurnoverOut)
async def get_aggregate_turnover(
    taxable: Decimal = Query(Decimal("0")),
    exempt: Decimal = Query(Decimal("0")),
    export: Decimal = Query(Decimal("0")),
    inter_state: Decimal = Query(Decimal("0")),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    result = compute_aggregate_turnover(taxable, exempt, export, inter_state, business.state_code)
    return AggregateTurnoverOut(
        taxable_value=result.taxable_value,
        exempt_value=result.exempt_value,
        export_value=result.export_value,
        inter_state_value=result.inter_state_value,
        aggregate_turnover=result.aggregate_turnover,
        is_registration_required=result.is_registration_required,
        registration_threshold=result.registration_threshold,
        is_composition_eligible=result.is_composition_eligible,
        state_code=result.state_code,
        hsn_requirement=result.hsn_requirement,
    )


@router.get("/itc-eligibility", response_model=ITCEligibilitySummaryOut)
async def get_itc_eligibility(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    records = await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business.id,
            InwardInvoice.period == period,
        )
    )
    invoices = records.all()

    items: list[ITCEligibilityItemOut] = []
    eligible_igst = eligible_cgst = eligible_sgst = Decimal("0")
    blocked_igst = blocked_cgst = blocked_sgst = Decimal("0")
    eligible_count = blocked_count = 0

    for inv in invoices:
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
        items.append(ITCEligibilityItemOut(
            invoice_id=result.invoice_id,
            supplier_name=result.supplier_name,
            invoice_number=result.invoice_number,
            invoice_date=result.invoice_date,
            igst=result.igst,
            cgst=result.cgst,
            sgst=result.sgst,
            is_eligible=result.is_eligible,
            blocked_reason=result.blocked_reason,
        ))
        if result.is_eligible:
            eligible_igst += result.igst
            eligible_cgst += result.cgst
            eligible_sgst += result.sgst
            eligible_count += 1
        else:
            blocked_igst += result.igst
            blocked_cgst += result.cgst
            blocked_sgst += result.sgst
            blocked_count += 1

    return ITCEligibilitySummaryOut(
        period=period,
        total_invoices=len(invoices),
        eligible_count=eligible_count,
        blocked_count=blocked_count,
        eligible_igst=eligible_igst,
        eligible_cgst=eligible_cgst,
        eligible_sgst=eligible_sgst,
        blocked_igst=blocked_igst,
        blocked_cgst=blocked_cgst,
        blocked_sgst=blocked_sgst,
        items=items,
    )


@router.get("/itc-setoff", response_model=ITCSetoffOut)
async def get_itc_setoff(
    igst_credit: Decimal = Query(Decimal("0")),
    cgst_credit: Decimal = Query(Decimal("0")),
    sgst_credit: Decimal = Query(Decimal("0")),
    igst_liability: Decimal = Query(Decimal("0")),
    cgst_liability: Decimal = Query(Decimal("0")),
    sgst_liability: Decimal = Query(Decimal("0")),
    current_user: User = Depends(get_current_user),
):
    result = compute_itc_setoff(
        igst_credit, cgst_credit, sgst_credit,
        igst_liability, cgst_liability, sgst_liability,
    )
    return ITCSetoffOut(
        igst_credit_used=result.igst_credit_used,
        cgst_credit_used=result.cgst_credit_used,
        sgst_credit_used=result.sgst_credit_used,
        igst_cash_required=result.igst_cash_required,
        cgst_cash_required=result.cgst_cash_required,
        sgst_cash_required=result.sgst_cash_required,
        igst_credit_remaining=result.igst_credit_remaining,
        cgst_credit_remaining=result.cgst_credit_remaining,
        sgst_credit_remaining=result.sgst_credit_remaining,
        total_cash_required=result.total_cash_required,
    )
