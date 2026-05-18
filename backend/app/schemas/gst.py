from pydantic import BaseModel
from decimal import Decimal
from datetime import date
from app.models.gst import ReconciliationStatus, IMSAction


class GSTR2BRecordOut(BaseModel):
    id: str
    supplier_gstin: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    taxable_value: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    period: str
    ims_action: IMSAction

    class Config:
        from_attributes = True


class ReconciliationResultOut(BaseModel):
    id: str
    period: str
    status: ReconciliationStatus
    match_confidence: int
    taxable_diff: Decimal
    tax_diff: Decimal
    notes: str | None
    resolved: bool
    supplier_name: str | None = None
    invoice_number: str | None = None

    class Config:
        from_attributes = True


class IMSActionRequest(BaseModel):
    record_id: str
    action: IMSAction


class ReconciliationSummary(BaseModel):
    period: str
    total_records: int
    matched: int
    missing_in_2b: int
    missing_in_books: int
    amount_mismatch: int
    pending_ims: int
    total_itc_eligible: Decimal
    total_itc_at_risk: Decimal
