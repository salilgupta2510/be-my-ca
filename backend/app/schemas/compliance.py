from pydantic import BaseModel
from datetime import date
from decimal import Decimal


class GSTINValidationOut(BaseModel):
    gstin: str
    is_valid: bool
    error: str | None
    state_code: str | None
    state_name: str | None
    pan: str | None


class DueDateOut(BaseModel):
    return_type: str
    period: str
    due_date: date
    days_remaining: int
    is_overdue: bool
    late_fee_applicable: bool


class LateFeeOut(BaseModel):
    return_type: str
    period: str
    due_date: date
    filing_date: date
    days_late: int
    late_fee_cgst: Decimal
    late_fee_sgst: Decimal
    late_fee_total: Decimal
    max_cap: Decimal
    is_nil_return: bool


class AggregateTurnoverOut(BaseModel):
    taxable_value: Decimal
    exempt_value: Decimal
    export_value: Decimal
    inter_state_value: Decimal
    aggregate_turnover: Decimal
    is_registration_required: bool
    registration_threshold: Decimal
    is_composition_eligible: bool
    state_code: str
    hsn_requirement: str


class ITCEligibilityItemOut(BaseModel):
    invoice_id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    is_eligible: bool
    blocked_reason: str


class ITCEligibilitySummaryOut(BaseModel):
    period: str
    total_invoices: int
    eligible_count: int
    blocked_count: int
    eligible_igst: Decimal
    eligible_cgst: Decimal
    eligible_sgst: Decimal
    blocked_igst: Decimal
    blocked_cgst: Decimal
    blocked_sgst: Decimal
    items: list[ITCEligibilityItemOut]


class ITCSetoffOut(BaseModel):
    igst_credit_used: Decimal
    cgst_credit_used: Decimal
    sgst_credit_used: Decimal
    igst_cash_required: Decimal
    cgst_cash_required: Decimal
    sgst_cash_required: Decimal
    igst_credit_remaining: Decimal
    cgst_credit_remaining: Decimal
    sgst_credit_remaining: Decimal
    total_cash_required: Decimal
