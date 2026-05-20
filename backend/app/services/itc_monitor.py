"""
ITC time-bar monitor — Section 16(4) CGST Act.

ITC must be claimed by the earlier of:
  (a) due date of GSTR-3B for September of the financial year following the year
      in which the invoice was issued, OR
  (b) date of filing the annual return (GSTR-9).

Practical rule applied here: 1 year from invoice date (conservative, standard interpretation).
Alert window: 60 days before expiry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import InwardInvoice
from app.services.gst_engine import check_itc_deadline

ALERT_DAYS_BEFORE = 60
LAPSED_REASON_PREFIX = "itc_lapsed"
EXPIRING_REASON_PREFIX = "itc_expiring_soon"


def _itc_deadline(invoice_date: date) -> date:
    """Conservative: 1 year from invoice date."""
    return date(invoice_date.year + 1, invoice_date.month, invoice_date.day)


def check_itc_expiry_at_create(invoice_date: date, check_date: date | None = None) -> str | None:
    """
    Called when an inward invoice is created.
    Returns a blocked_reason string if ITC is already lapsed or about to lapse,
    else None.
    """
    today = check_date or date.today()
    deadline = _itc_deadline(invoice_date)
    if today > deadline:
        return f"{LAPSED_REASON_PREFIX}:{deadline.isoformat()}"
    days_left = (deadline - today).days
    if days_left <= ALERT_DAYS_BEFORE:
        return f"{EXPIRING_REASON_PREFIX}:{deadline.isoformat()}"
    return None


@dataclass
class ITCExpiryAlert:
    invoice_id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    itc_deadline: date
    days_remaining: int
    is_lapsed: bool
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    total_itc_at_risk: Decimal


async def scan_itc_expiry(
    db: AsyncSession,
    business_id: str,
    check_date: date | None = None,
) -> list[ITCExpiryAlert]:
    """
    Scan all eligible inward invoices for a business.
    Returns alerts for invoices that are lapsed or expiring within ALERT_DAYS_BEFORE days.
    Also writes the lapse reason back to the DB for any newly lapsed invoices.
    """
    today = check_date or date.today()

    invoices = (await db.scalars(
        select(InwardInvoice).where(
            InwardInvoice.business_id == business_id,
        )
    )).all()

    alerts: list[ITCExpiryAlert] = []
    updated: list[InwardInvoice] = []

    for inv in invoices:
        # Skip already-blocked (Section 17(5) etc) — only track time-bar
        reason = inv.itc_blocked_reason or ""
        if reason and not reason.startswith(EXPIRING_REASON_PREFIX) and not reason.startswith(LAPSED_REASON_PREFIX):
            continue

        deadline = _itc_deadline(inv.invoice_date)
        days_left = (deadline - today).days
        is_lapsed = days_left < 0

        if is_lapsed or days_left <= ALERT_DAYS_BEFORE:
            new_reason = (
                f"{LAPSED_REASON_PREFIX}:{deadline.isoformat()}"
                if is_lapsed
                else f"{EXPIRING_REASON_PREFIX}:{deadline.isoformat()}"
            )
            if inv.itc_blocked_reason != new_reason:
                inv.itc_blocked_reason = new_reason
                updated.append(inv)

            alerts.append(ITCExpiryAlert(
                invoice_id=str(inv.id),
                supplier_name=inv.supplier_name,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                itc_deadline=deadline,
                days_remaining=days_left,
                is_lapsed=is_lapsed,
                igst=inv.igst,
                cgst=inv.cgst,
                sgst=inv.sgst,
                total_itc_at_risk=inv.igst + inv.cgst + inv.sgst,
            ))

    if updated:
        await db.commit()

    # Sort: lapsed first, then by days_remaining ascending
    alerts.sort(key=lambda a: (not a.is_lapsed, a.days_remaining))
    return alerts
