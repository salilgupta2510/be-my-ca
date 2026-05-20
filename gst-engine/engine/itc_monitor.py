"""
ITC time-bar monitor — Section 16(4) CGST Act.
Decoupled from SQLAlchemy: accepts plain InwardInvoiceData list.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .gstr_compute import InwardInvoiceData

ALERT_DAYS_BEFORE = 60
LAPSED_REASON_PREFIX = "itc_lapsed"
EXPIRING_REASON_PREFIX = "itc_expiring_soon"


def _itc_deadline(invoice_date: date) -> date:
    """Conservative: 1 year from invoice date."""
    return date(invoice_date.year + 1, invoice_date.month, invoice_date.day)


def check_itc_expiry_at_create(invoice_date: date, check_date: date | None = None) -> str | None:
    """
    Returns blocked_reason string if ITC is lapsed/expiring, else None.
    Call when creating an inward invoice.
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
    new_blocked_reason: str | None  # set if reason changed, for DB write-back


def scan_itc_expiry(
    invoices: list[InwardInvoiceData],
    check_date: date | None = None,
) -> list[ITCExpiryAlert]:
    """
    Pure function: scan invoices for ITC time-bar risk.
    Returns alerts sorted: lapsed first, then by days_remaining ascending.
    `new_blocked_reason` is set if the stored reason needs updating in DB.
    """
    today = check_date or date.today()
    alerts: list[ITCExpiryAlert] = []

    for inv in invoices:
        # Skip already-blocked for Section 17(5) etc — only track time-bar
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
            alerts.append(ITCExpiryAlert(
                invoice_id=inv.id,
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
                new_blocked_reason=new_reason if inv.itc_blocked_reason != new_reason else None,
            ))

    alerts.sort(key=lambda a: (not a.is_lapsed, a.days_remaining))
    return alerts
