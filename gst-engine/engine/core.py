"""
GST law engine — implements core Indian GST rules per CGST Act 2017.
Rules-aware: all constants loaded from RulesBundle, not hardcoded.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from .rules_loader import RulesBundle, get_rules

# ─── GSTIN Validation ─────────────────────────────────────────────────────────

GSTIN_PATTERN = re.compile(
    r"^(\d{2})([A-Z]{5}\d{4}[A-Z])(\d)([Z])([A-Z\d])$"
)


def validate_gstin(gstin: str, rules: RulesBundle | None = None) -> tuple[bool, str]:
    rules = rules or get_rules()
    if not gstin:
        return False, "GSTIN is required"
    gstin = gstin.upper().strip()
    if len(gstin) != 15:
        return False, f"GSTIN must be 15 characters, got {len(gstin)}"
    m = GSTIN_PATTERN.match(gstin)
    if not m:
        return False, "GSTIN format invalid. Expected: 2-digit state + 10-char PAN + sequence + Z + check"
    state_code = m.group(1)
    if state_code not in rules.state_codes:
        return False, f"Invalid state code '{state_code}' in GSTIN"
    return True, ""


def get_state_from_gstin(gstin: str) -> str | None:
    if gstin and len(gstin) >= 2:
        return gstin[:2]
    return None


def get_state_name(state_code: str, rules: RulesBundle | None = None) -> str:
    rules = rules or get_rules()
    return rules.state_codes.get(state_code, f"State {state_code}")


# ─── Place of Supply ──────────────────────────────────────────────────────────

SupplyType = Literal["intra", "inter"]


def determine_supply_type(business_state: str, recipient_state: str) -> SupplyType:
    return "intra" if business_state == recipient_state else "inter"


def compute_tax_for_supply(
    supply_type: SupplyType,
    taxable_value: Decimal,
    rate_pct: Decimal,
) -> dict[str, Decimal]:
    total_tax = (taxable_value * rate_pct / 100).quantize(Decimal("0.01"))
    if supply_type == "inter":
        return {"igst": total_tax, "cgst": Decimal("0"), "sgst": Decimal("0")}
    half = (total_tax / 2).quantize(Decimal("0.01"))
    return {"igst": Decimal("0"), "cgst": half, "sgst": total_tax - half}


# ─── ITC Set-Off (Section 49) ─────────────────────────────────────────────────

@dataclass
class ITCSetoff:
    igst_credit_used: Decimal = Decimal("0")
    cgst_credit_used: Decimal = Decimal("0")
    sgst_credit_used: Decimal = Decimal("0")
    igst_cash_required: Decimal = Decimal("0")
    cgst_cash_required: Decimal = Decimal("0")
    sgst_cash_required: Decimal = Decimal("0")
    igst_credit_remaining: Decimal = Decimal("0")
    cgst_credit_remaining: Decimal = Decimal("0")
    sgst_credit_remaining: Decimal = Decimal("0")
    total_cash_required: Decimal = Decimal("0")


def compute_itc_setoff(
    igst_credit: Decimal,
    cgst_credit: Decimal,
    sgst_credit: Decimal,
    igst_liability: Decimal,
    cgst_liability: Decimal,
    sgst_liability: Decimal,
) -> ITCSetoff:
    """Section 49 CGST Act set-off order — 5 steps."""
    D = Decimal
    result = ITCSetoff()

    igst_rem, cgst_rem, sgst_rem = igst_credit, cgst_credit, sgst_credit
    igst_liab, cgst_liab, sgst_liab = igst_liability, cgst_liability, sgst_liability

    # Step 1: IGST → IGST
    applied = min(igst_rem, igst_liab)
    result.igst_credit_used += applied; igst_rem -= applied; igst_liab -= applied

    # Step 2: IGST → CGST
    applied = min(igst_rem, cgst_liab)
    result.igst_credit_used += applied; igst_rem -= applied; cgst_liab -= applied

    # Step 3: IGST → SGST
    applied = min(igst_rem, sgst_liab)
    result.igst_credit_used += applied; igst_rem -= applied; sgst_liab -= applied

    # Step 4: CGST → CGST
    applied = min(cgst_rem, cgst_liab)
    result.cgst_credit_used += applied; cgst_rem -= applied; cgst_liab -= applied

    # Step 5: SGST → SGST
    applied = min(sgst_rem, sgst_liab)
    result.sgst_credit_used += applied; sgst_rem -= applied; sgst_liab -= applied

    result.igst_credit_remaining = igst_rem
    result.cgst_credit_remaining = cgst_rem
    result.sgst_credit_remaining = sgst_rem
    result.igst_cash_required = max(D("0"), igst_liab)
    result.cgst_cash_required = max(D("0"), cgst_liab)
    result.sgst_cash_required = max(D("0"), sgst_liab)
    result.total_cash_required = (
        result.igst_cash_required + result.cgst_cash_required + result.sgst_cash_required
    )
    return result


# ─── ITC Eligibility ──────────────────────────────────────────────────────────

def is_itc_blocked(category: str, rules: RulesBundle | None = None) -> bool:
    rules = rules or get_rules()
    return category in rules.itc_blocked_categories


def check_itc_deadline(invoice_date: date, check_date: date | None = None) -> tuple[bool, str]:
    """Section 16(4): 1 year from invoice date."""
    if check_date is None:
        check_date = date.today()
    deadline = date(invoice_date.year + 1, invoice_date.month, invoice_date.day)
    if check_date > deadline:
        return False, f"ITC time-barred: invoice date {invoice_date}, deadline was {deadline}"
    return True, ""


@dataclass
class ITCEligibilityResult:
    invoice_id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    is_eligible: bool
    blocked_reason: str = ""


def check_itc_eligibility(
    invoice_id: str,
    supplier_name: str,
    invoice_number: str,
    invoice_date: date,
    igst: Decimal,
    cgst: Decimal,
    sgst: Decimal,
    itc_category: str | None = None,
    is_rcm: bool = False,
    check_date: date | None = None,
    rules: RulesBundle | None = None,
) -> ITCEligibilityResult:
    rules = rules or get_rules()
    check_date = check_date or date.today()

    eligible, reason = check_itc_deadline(invoice_date, check_date)
    if not eligible:
        return ITCEligibilityResult(
            invoice_id=invoice_id, supplier_name=supplier_name,
            invoice_number=invoice_number, invoice_date=invoice_date,
            igst=igst, cgst=cgst, sgst=sgst,
            is_eligible=False, blocked_reason=reason,
        )

    if itc_category and is_itc_blocked(itc_category, rules):
        return ITCEligibilityResult(
            invoice_id=invoice_id, supplier_name=supplier_name,
            invoice_number=invoice_number, invoice_date=invoice_date,
            igst=igst, cgst=cgst, sgst=sgst,
            is_eligible=False,
            blocked_reason=f"ITC blocked under Section 17(5): {itc_category}",
        )

    return ITCEligibilityResult(
        invoice_id=invoice_id, supplier_name=supplier_name,
        invoice_number=invoice_number, invoice_date=invoice_date,
        igst=igst, cgst=cgst, sgst=sgst, is_eligible=True,
    )


# ─── Return Due Dates ─────────────────────────────────────────────────────────

def _period_to_date(period: str) -> date:
    year, month = period.split("-")
    return date(int(year), int(month), 1)


def _next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def get_return_due_date(period: str, return_type: str, rules: RulesBundle | None = None) -> date:
    rules = rules or get_rules()
    dd = rules.due_dates
    rt = return_type.lower()

    if rt in ("gstr1", "gstr3b", "gstr4", "gstr6", "gstr7"):
        p = _period_to_date(period)
        nm = _next_month(p)
        day_key = f"{rt}_day_of_next_month"
        day = dd.get(day_key, {"gstr1": 11, "gstr3b": 20, "gstr4": 18, "gstr6": 13, "gstr7": 10}[rt])
        return date(nm.year, nm.month, day)

    if rt == "gstr9":
        year = int(period.split("-")[0])
        return date(year + 1, dd.get("gstr9_month", 12), dd.get("gstr9_day", 31))

    raise ValueError(f"Unknown return type: {return_type}")


@dataclass
class DueDateInfo:
    return_type: str
    period: str
    due_date: date
    days_remaining: int
    is_overdue: bool
    late_fee_applicable: bool = True


def get_compliance_calendar(
    period: str,
    is_composition: bool = False,
    rules: RulesBundle | None = None,
) -> list[DueDateInfo]:
    rules = rules or get_rules()
    today = date.today()
    returns = []

    if is_composition:
        due = get_return_due_date(period, "gstr4", rules)
        remaining = (due - today).days
        returns.append(DueDateInfo(
            return_type="GSTR-4", period=period, due_date=due,
            days_remaining=remaining, is_overdue=remaining < 0,
        ))
    else:
        for rt_key, rt_label in [("gstr1", "GSTR-1"), ("gstr3b", "GSTR-3B")]:
            due = get_return_due_date(period, rt_key, rules)
            remaining = (due - today).days
            returns.append(DueDateInfo(
                return_type=rt_label, period=period, due_date=due,
                days_remaining=remaining, is_overdue=remaining < 0,
            ))

    return returns


# ─── Late Fee (Section 47) ────────────────────────────────────────────────────

@dataclass
class LateFeeResult:
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


def compute_late_fee(
    return_type: str,
    period: str,
    filing_date: date,
    is_nil_return: bool = False,
    annual_turnover: Decimal | None = None,
    rules: RulesBundle | None = None,
) -> LateFeeResult:
    rules = rules or get_rules()
    lf = rules.late_fee
    D = Decimal

    due_date = get_return_due_date(period, return_type.lower().replace("-", ""), rules)
    days_late = max(0, (filing_date - due_date).days)

    zero = D("0")
    if days_late == 0:
        return LateFeeResult(
            return_type=return_type, period=period, due_date=due_date,
            filing_date=filing_date, days_late=0,
            late_fee_cgst=zero, late_fee_sgst=zero, late_fee_total=zero,
            max_cap=zero, is_nil_return=is_nil_return,
        )

    rt = return_type.lower().replace("-", "")

    if rt == "gstr9":
        daily = D(str(lf.get("gstr9_daily_total", 200)))
        fee = D(days_late) * daily
        cap = zero
        if annual_turnover:
            cap = (annual_turnover * D(str(lf.get("gstr9_max_pct_of_turnover", 0.25))) / 100).quantize(D("0.01"))
            fee = min(fee, cap)
        half = (fee / 2).quantize(D("0.01"))
        return LateFeeResult(
            return_type=return_type, period=period, due_date=due_date,
            filing_date=filing_date, days_late=days_late,
            late_fee_cgst=half, late_fee_sgst=fee - half,
            late_fee_total=fee, max_cap=cap, is_nil_return=False,
        )

    nil_key = "nil" if is_nil_return else "nonnl"
    rt_short = rt if rt in ("gstr1", "gstr3b", "gstr4") else "gstr1"
    daily_each = D(str(lf.get(f"{rt_short}_{nil_key}_daily_each_act", 10 if is_nil_return else 25)))
    max_each = D(str(lf.get(f"{rt_short}_{nil_key}_max_each", 500 if is_nil_return else 1000)))

    if annual_turnover is not None:
        slab1 = D(str(lf.get("turnover_slab_1_crore", 15000000)))
        slab2 = D(str(lf.get("turnover_slab_2_crore", 50000000)))
        if annual_turnover <= slab1:
            max_total = D(str(lf.get("turnover_slab_1_max_total", 2000)))
        elif annual_turnover <= slab2:
            max_total = D(str(lf.get("turnover_slab_2_max_total", 5000)))
        else:
            max_total = D(str(lf.get("turnover_slab_3_max_total", 10000)))
        max_each = min(max_each, max_total / 2)

    fee_each = min(D(days_late) * daily_each, max_each)
    total = fee_each * 2

    return LateFeeResult(
        return_type=return_type, period=period, due_date=due_date,
        filing_date=filing_date, days_late=days_late,
        late_fee_cgst=fee_each, late_fee_sgst=fee_each,
        late_fee_total=total, max_cap=max_each * 2, is_nil_return=is_nil_return,
    )


# ─── Aggregate Turnover ────────────────────────────────────────────────────────

@dataclass
class AggregateTurnoverResult:
    taxable_value: Decimal
    exempt_value: Decimal
    export_value: Decimal
    inter_state_value: Decimal
    aggregate_turnover: Decimal
    is_registration_required: bool
    registration_threshold: Decimal
    is_composition_eligible: bool
    state_code: str
    hsn_requirement: str  # "none" | "2_digit" | "4_digit"


def compute_aggregate_turnover(
    taxable_value: Decimal,
    exempt_value: Decimal,
    export_value: Decimal,
    inter_state_value: Decimal,
    state_code: str = "27",
    rules: RulesBundle | None = None,
) -> AggregateTurnoverResult:
    rules = rules or get_rules()
    aggregate = taxable_value + exempt_value + export_value + inter_state_value

    threshold = (
        rules.special_registration if state_code in rules.special_category_states
        else rules.normal_registration
    )

    if aggregate >= rules.hsn_mandatory_threshold:
        hsn_req = "4_digit"
    elif aggregate >= rules.hsn_optional_threshold:
        hsn_req = "2_digit"
    else:
        hsn_req = "none"

    return AggregateTurnoverResult(
        taxable_value=taxable_value,
        exempt_value=exempt_value,
        export_value=export_value,
        inter_state_value=inter_state_value,
        aggregate_turnover=aggregate,
        is_registration_required=aggregate >= threshold,
        registration_threshold=threshold,
        is_composition_eligible=aggregate < rules.composition_threshold and aggregate >= Decimal("0"),
        state_code=state_code,
        hsn_requirement=hsn_req,
    )


# ─── Composition Scheme ────────────────────────────────────────────────────────

@dataclass
class CompositionInfo:
    is_eligible: bool
    reason: str
    applicable_rate: Decimal | None
    restrictions: list[str]
    return_form: str


def get_composition_info(
    aggregate_turnover: Decimal,
    business_type: str = "trader",
    has_inter_state_supply: bool = False,
    has_ecommerce_supply: bool = False,
    rules: RulesBundle | None = None,
) -> CompositionInfo:
    rules = rules or get_rules()
    restrictions = [
        "Cannot make inter-state supplies",
        "Cannot issue tax invoice (use Bill of Supply)",
        "Cannot collect GST from buyer",
        "Cannot claim input tax credit",
        "Cannot supply through e-commerce operator",
    ]

    if aggregate_turnover >= rules.composition_threshold:
        return CompositionInfo(
            is_eligible=False,
            reason=f"Aggregate turnover ₹{aggregate_turnover:,.0f} exceeds composition threshold",
            applicable_rate=None, restrictions=[], return_form="GSTR-3B",
        )

    if has_inter_state_supply:
        return CompositionInfo(
            is_eligible=False,
            reason="Inter-state suppliers cannot opt for composition scheme",
            applicable_rate=None, restrictions=[], return_form="GSTR-3B",
        )

    if has_ecommerce_supply:
        return CompositionInfo(
            is_eligible=False,
            reason="Suppliers through e-commerce operator cannot use composition scheme",
            applicable_rate=None, restrictions=[], return_form="GSTR-3B",
        )

    rate = rules.composition_rates.get(business_type, rules.composition_rates.get("trader", Decimal("1.0")))
    return CompositionInfo(
        is_eligible=True,
        reason=f"Eligible for composition scheme. Turnover ₹{aggregate_turnover:,.0f} < threshold",
        applicable_rate=rate, restrictions=restrictions, return_form="GSTR-4 (quarterly)",
    )


# ─── Credit Note ITC Reversal ─────────────────────────────────────────────────

@dataclass
class CreditNoteITCReversal:
    credit_note_number: str
    original_invoice_ref: str | None
    reversal_igst: Decimal
    reversal_cgst: Decimal
    reversal_sgst: Decimal
    reversal_total: Decimal
    is_traceable: bool
    is_allowed: bool
    reason: str


def compute_credit_note_reversal(
    credit_note_number: str,
    discount_amount: Decimal,
    tax_rate_pct: Decimal,
    original_invoice_ref: str | None,
    supply_type: SupplyType,
    is_agreed_before_supply: bool,
) -> CreditNoteITCReversal:
    """Section 15(3) post-supply discount ITC reversal rules."""
    if is_agreed_before_supply and original_invoice_ref:
        breakdown = compute_tax_for_supply(supply_type, discount_amount, tax_rate_pct)
        return CreditNoteITCReversal(
            credit_note_number=credit_note_number,
            original_invoice_ref=original_invoice_ref,
            reversal_igst=breakdown["igst"],
            reversal_cgst=breakdown["cgst"],
            reversal_sgst=breakdown["sgst"],
            reversal_total=breakdown["igst"] + breakdown["cgst"] + breakdown["sgst"],
            is_traceable=True, is_allowed=True,
            reason="Discount agreed before supply and traceable. ITC reversal required from buyer.",
        )
    return CreditNoteITCReversal(
        credit_note_number=credit_note_number,
        original_invoice_ref=original_invoice_ref,
        reversal_igst=Decimal("0"), reversal_cgst=Decimal("0"), reversal_sgst=Decimal("0"),
        reversal_total=Decimal("0"), is_traceable=False, is_allowed=False,
        reason="Post-supply discount not known at time of supply — not deductible from transaction value.",
    )
