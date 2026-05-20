"""
DB-coupled ITC time-bar monitor.
Wraps the pure engine.itc_monitor functions with SQLAlchemy session handling.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import InwardInvoice
from engine.gstr_compute import InwardInvoiceData
from engine.itc_monitor import (
    scan_itc_expiry as _scan_itc_expiry,
    check_itc_expiry_at_create,  # noqa: F401 — re-exported for callers
    ITCExpiryAlert,              # noqa: F401
    ALERT_DAYS_BEFORE,           # noqa: F401
    LAPSED_REASON_PREFIX,        # noqa: F401
    EXPIRING_REASON_PREFIX,      # noqa: F401
)


async def scan_itc_expiry(
    db: AsyncSession,
    business_id: str,
    check_date: date | None = None,
) -> list[ITCExpiryAlert]:
    """
    DB wrapper: loads InwardInvoice rows, delegates to pure engine,
    then writes back any updated blocked reasons.
    """
    invoices_orm = (await db.scalars(
        select(InwardInvoice).where(InwardInvoice.business_id == business_id)
    )).all()

    # Map ORM → plain dataclasses
    invoice_data = [
        InwardInvoiceData(
            id=str(inv.id),
            supplier_name=inv.supplier_name,
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date,
            period=inv.period,
            igst=inv.igst,
            cgst=inv.cgst,
            sgst=inv.sgst,
            supplier_gstin=inv.supplier_gstin,
            itc_blocked_reason=inv.itc_blocked_reason,
            is_rcm=inv.is_rcm,
        )
        for inv in invoices_orm
    ]

    alerts = _scan_itc_expiry(invoice_data, check_date)

    # Write-back: update ORM rows where blocked reason changed
    orm_by_id = {str(inv.id): inv for inv in invoices_orm}
    updated = False
    for alert in alerts:
        if alert.new_blocked_reason is not None:
            orm_inv = orm_by_id.get(alert.invoice_id)
            if orm_inv:
                orm_inv.itc_blocked_reason = alert.new_blocked_reason
                updated = True

    if updated:
        await db.commit()

    return alerts
