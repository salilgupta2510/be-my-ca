"""
GST law engine — implements core Indian GST rules per CGST Act 2017.
All monetary amounts in INR. Period format: YYYY-MM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

# ─── Constants ────────────────────────────────────────────────────────────────

# State code → state name (Census 2011)
STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli",
    "27": "Maharashtra", "28": "Andhra Pradesh (old)",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman & Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory", "99": "Centre Jurisdiction",
}

# Special category states with ₹10L registration threshold
SPECIAL_CATEGORY_STATES = {
    "01", "02", "11", "12", "13", "14", "15", "16", "17", "18",
    "05",  # Uttarakhand
}

# GST standard tax rates (%)
STANDARD_RATES = {0, 5, 12, 18, 28}

# Composition rates (CGST+SGST combined)
COMPOSITION_RATES = {
    "manufacturer": Decimal("1.0"),    # 0.5% CGST + 0.5% SGST each
    "restaurant": Decimal("5.0"),      # 2.5% CGST + 2.5% SGST each
    "trader": Decimal("1.0"),          # 0.5% CGST + 0.5% SGST each
    "other_services": Decimal("6.0"),  # 3% CGST + 3% SGST (QRMP scheme)
}

# Aggregate turnover thresholds
COMPOSITION_THRESHOLD = Decimal("50_00_000")      # ₹50 lakh
NORMAL_REG_THRESHOLD = Decimal("20_00_000")       # ₹20 lakh
SPECIAL_REG_THRESHOLD = Decimal("10_00_000")      # ₹10 lakh (special states)
HSN_MANDATORY_THRESHOLD = Decimal("5_00_00_000")  # ₹5 crore (4-digit HSN)
HSN_OPTIONAL_THRESHOLD = Decimal("1_50_00_000")   # ₹1.5 crore (2-digit HSN)

# ITC blocked categories (Section 17(5) CGST Act)
ITC_BLOCKED_CATEGORIES = {
    "motor_vehicle",        # motor vehicles < 13 passengers, except listed exceptions
    "food_beverages",       # food, beverages, outdoor catering, beauty treatment
    "health_fitness",       # club, health, fitness membership
    "rent_a_cab",           # rent-a-cab (unless obligatory employer)
    "life_insurance",       # life insurance, health insurance (unless obligatory)
    "travel_benefit",       # leave travel concession for employees
    "works_contract",       # works contract for immovable property
    "immovable_property",   # goods/services for construction of immovable property
    "composition",          # buyer is composition dealer
    "personal_use",         # goods/services for personal consumption
    "free_samples",         # goods disposed as gift/free samples
}


# ─── GSTIN Validation ─────────────────────────────────────────────────────────

GSTIN_PATTERN = re.compile(
    r"^(\d{2})([A-Z]{5}\d{4}[A-Z])(\d)([Z])([A-Z\d])$"
)


def validate_gstin(gstin: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Structure: [state:2][PAN:10][seq:1][Z][check:1]
    """
    if not gstin:
        return False, "GSTIN is required"
    gstin = gstin.upper().strip()
    if len(gstin) != 15:
        return False, f"GSTIN must be 15 characters, got {len(gstin)}"
    m = GSTIN_PATTERN.match(gstin)
    if not m:
        return False, "GSTIN format invalid. Expected: 2-digit state + 10-char PAN + sequence + Z + check"
    state_code = m.group(1)
    if state_code not in STATE_CODES:
        return False, f"Invalid state code '{state_code}' in GSTIN"
    return True, ""


def get_state_from_gstin(gstin: str) -> str | None:
    if gstin and len(gstin) >= 2:
        return gstin[:2]
    return None


def get_state_name(state_code: str) -> str:
    return STATE_CODES.get(state_code, f"State {state_code}")


# ─── Place of Supply ──────────────────────────────────────────────────────────

SupplyType = Literal["intra", "inter"]


def determine_supply_type(business_state: str, recipient_state: str) -> SupplyType:
    """
    Compare supplier state vs recipient/place-of-supply state.
    Same state → intra (CGST+SGST). Different → inter (IGST).
    """
    return "intra" if business_state == recipient_state else "inter"


def compute_tax_for_supply(
    supply_type: SupplyType,
    taxable_value: Decimal,
    rate_pct: Decimal,
) -> dict[str, Decimal]:
    """
    Returns igst/cgst/sgst breakdown based on supply type.
    rate_pct is the total GST rate (e.g. 18 for 18%).
    """
    total_tax = (taxable_value * rate_pct / 100).quantize(Decimal("0.01"))
    if supply_type == "inter":
        return {"igst": total_tax, "cgst": Decimal("0"), "sgst": Decimal("0")}
    half = (total_tax / 2).quantize(Decimal("0.01"))
    # Handle rounding: CGST + SGST = total_tax
    other_half = total_tax - half
    return {"igst": Decimal("0"), "cgst": half, "sgst": other_half}


# ─── ITC Set-Off Order (Section 49 CGST Act) ──────────────────────────────────

@dataclass
class ITCSetoff:
    """Result of ITC set-off computation."""
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
    """
    Apply ITC set-off in legal order (Section 49 CGST Act):
    1. IGST credit → IGST liability first
    2. Remaining IGST credit → CGST liability
    3. Any further IGST credit → SGST liability
    4. CGST credit → CGST liability only
    5. SGST credit → SGST liability only
    CGST credit cannot offset SGST and vice versa.
    """
    D = Decimal
    result = ITCSetoff()

    igst_rem = igst_credit
    cgst_rem = cgst_credit
    sgst_rem = sgst_credit
    igst_liab = igst_liability
    cgst_liab = cgst_liability
    sgst_liab = sgst_liability

    # Step 1: IGST credit → IGST liability
    applied = min(igst_rem, igst_liab)
    result.igst_credit_used += applied
    igst_rem -= applied
    igst_liab -= applied

    # Step 2: Remaining IGST credit → CGST liability
    applied = min(igst_rem, cgst_liab)
    result.igst_credit_used += applied
    igst_rem -= applied
    cgst_liab -= applied

    # Step 3: Remaining IGST credit → SGST liability
    applied = min(igst_rem, sgst_liab)
    result.igst_credit_used += applied
    igst_rem -= applied
    sgst_liab -= applied

    # Step 4: CGST credit → remaining CGST liability
    applied = min(cgst_rem, cgst_liab)
    result.cgst_credit_used += applied
    cgst_rem -= applied
    cgst_liab -= applied

    # Step 5: SGST credit → remaining SGST liability
    applied = min(sgst_rem, sgst_liab)
    result.sgst_credit_used += applied
    sgst_rem -= applied
    sgst_liab -= applied

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

def is_itc_blocked(category: str) -> bool:
    """Returns True if ITC is blocked for this category under Section 17(5)."""
    return category in ITC_BLOCKED_CATEGORIES


def check_itc_deadline(invoice_date: date, check_date: date | None = None) -> tuple[bool, str]:
    """
    ITC must be claimed within 1 year of invoice date (Section 16(4)).
    Returns (is_eligible, reason).
    """
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
) -> ITCEligibilityResult:
    """
    Comprehensive ITC eligibility check for a single inward invoice.
    """
    check_date = check_date or date.today()

    # Check time limit
    eligible, reason = check_itc_deadline(invoice_date, check_date)
    if not eligible:
        return ITCEligibilityResult(
            invoice_id=invoice_id, supplier_name=supplier_name,
            invoice_number=invoice_number, invoice_date=invoice_date,
            igst=igst, cgst=cgst, sgst=sgst,
            is_eligible=False, blocked_reason=reason,
        )

    # Check blocked category
    if itc_category and is_itc_blocked(itc_category):
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
        igst=igst, cgst=cgst, sgst=sgst,
        is_eligible=True,
    )


# ─── Return Due Dates ─────────────────────────────────────────────────────────

def _period_to_date(period: str) -> date:
    """'2025-01' → date(2025, 1, 1)"""
    year, month = period.split("-")
    return date(int(year), int(month), 1)


def _next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def get_return_due_date(period: str, return_type: str) -> date:
    """
    Returns due date for a given return type and period.
    return_type: gstr1 | gstr3b | gstr4 | gstr6 | gstr7 | gstr9
    period: YYYY-MM (for monthly) or YYYY-QN for quarterly (e.g. 2025-Q1)
    """
    rt = return_type.lower()

    if rt == "gstr1":
        # 10th of next month
        p = _period_to_date(period)
        nm = _next_month(p)
        return date(nm.year, nm.month, 11)

    elif rt == "gstr3b":
        # 20th of next month
        p = _period_to_date(period)
        nm = _next_month(p)
        return date(nm.year, nm.month, 20)

    elif rt == "gstr4":
        # 18th of month following the quarter
        # period YYYY-MM (last month of quarter)
        p = _period_to_date(period)
        nm = _next_month(p)
        return date(nm.year, nm.month, 18)

    elif rt == "gstr6":
        # 13th of next month (ISD)
        p = _period_to_date(period)
        nm = _next_month(p)
        return date(nm.year, nm.month, 13)

    elif rt == "gstr7":
        # 10th of next month (TDS deductors)
        p = _period_to_date(period)
        nm = _next_month(p)
        return date(nm.year, nm.month, 10)

    elif rt == "gstr9":
        # 31st December of next FY (annual)
        year = int(period.split("-")[0])
        return date(year + 1, 12, 31)

    raise ValueError(f"Unknown return type: {return_type}")


@dataclass
class DueDateInfo:
    return_type: str
    period: str
    due_date: date
    days_remaining: int
    is_overdue: bool
    late_fee_applicable: bool = True


def get_compliance_calendar(period: str, is_composition: bool = False) -> list[DueDateInfo]:
    """Returns due dates for all applicable returns for a given period."""
    today = date.today()
    returns = []

    if is_composition:
        # Composition: only GSTR-4 (quarterly)
        # period should be last month of quarter (e.g. 2025-03 for Q4)
        due = get_return_due_date(period, "gstr4")
        remaining = (due - today).days
        returns.append(DueDateInfo(
            return_type="GSTR-4", period=period, due_date=due,
            days_remaining=remaining, is_overdue=remaining < 0,
        ))
    else:
        for rt_key, rt_label in [("gstr1", "GSTR-1"), ("gstr3b", "GSTR-3B")]:
            due = get_return_due_date(period, rt_key)
            remaining = (due - today).days
            returns.append(DueDateInfo(
                return_type=rt_label, period=period, due_date=due,
                days_remaining=remaining, is_overdue=remaining < 0,
            ))

    return returns


# ─── Late Fee Computation ─────────────────────────────────────────────────────

@dataclass
class LateFeeResult:
    return_type: str
    period: str
    due_date: date
    filing_date: date
    days_late: int
    late_fee_cgst: Decimal   # ₹ per day per act
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
) -> LateFeeResult:
    """
    Section 47 CGST Act late fee rules:
    - GSTR-1/3B nil return: ₹10/day each act (₹20/day total), max ₹500 each (₹1000 total)
    - GSTR-1/3B non-nil: ₹25/day each act (₹50/day total), max ₹1000 each (₹2000 total)
    - Turnover ≤ ₹1.5Cr: max ₹2000 total (per notification)
    - Turnover ₹1.5Cr–₹5Cr: max ₹5000 total
    - Turnover > ₹5Cr: max ₹10000 total
    - GSTR-9 annual: ₹200/day, max 0.25% of turnover
    """
    D = Decimal
    due_date = get_return_due_date(period, return_type.lower().replace("-", ""))
    days_late = max(0, (filing_date - due_date).days)

    if days_late == 0:
        zero = D("0")
        return LateFeeResult(
            return_type=return_type, period=period, due_date=due_date,
            filing_date=filing_date, days_late=0,
            late_fee_cgst=zero, late_fee_sgst=zero, late_fee_total=zero,
            max_cap=zero, is_nil_return=is_nil_return,
        )

    rt = return_type.lower().replace("-", "")

    if rt == "gstr9":
        # Annual return: ₹200/day (₹100 CGST + ₹100 SGST)
        daily = D("200")
        fee = D(days_late) * daily
        cap = D("0")
        if annual_turnover:
            cap = (annual_turnover * D("0.0025")).quantize(D("0.01"))
            fee = min(fee, cap)
        half = (fee / 2).quantize(D("0.01"))
        return LateFeeResult(
            return_type=return_type, period=period, due_date=due_date,
            filing_date=filing_date, days_late=days_late,
            late_fee_cgst=half, late_fee_sgst=fee - half,
            late_fee_total=fee, max_cap=cap, is_nil_return=False,
        )

    # GSTR-1, GSTR-3B, GSTR-4
    if is_nil_return:
        daily_each = D("10")  # ₹10/day per act (CGST + SGST)
        max_each = D("500")
    else:
        daily_each = D("25")
        max_each = D("1000")

    # Turnover-based cap
    if annual_turnover is not None:
        if annual_turnover <= D("1_50_00_000"):
            max_total = D("2000")
        elif annual_turnover <= D("5_00_00_000"):
            max_total = D("5000")
        else:
            max_total = D("10000")
        max_each = min(max_each, max_total / 2)

    fee_each = min(D(days_late) * daily_each, max_each)
    total = fee_each * 2  # CGST + SGST

    return LateFeeResult(
        return_type=return_type, period=period, due_date=due_date,
        filing_date=filing_date, days_late=days_late,
        late_fee_cgst=fee_each, late_fee_sgst=fee_each,
        late_fee_total=total, max_cap=max_each * 2,
        is_nil_return=is_nil_return,
    )


# ─── Aggregate Turnover ────────────────────────────────────────────────────────

@dataclass
class AggregateTurnoverResult:
    taxable_value: Decimal
    exempt_value: Decimal
    export_value: Decimal
    inter_state_value: Decimal
    aggregate_turnover: Decimal  # excludes taxes + inward RCM
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
) -> AggregateTurnoverResult:
    """
    Aggregate turnover = taxable supplies + exempt supplies + exports + inter-state
    (all on same PAN, all-India basis, excluding taxes and inward RCM supplies).
    """
    aggregate = taxable_value + exempt_value + export_value + inter_state_value

    threshold = (
        SPECIAL_REG_THRESHOLD if state_code in SPECIAL_CATEGORY_STATES
        else NORMAL_REG_THRESHOLD
    )

    if aggregate >= HSN_MANDATORY_THRESHOLD:
        hsn_req = "4_digit"
    elif aggregate >= HSN_OPTIONAL_THRESHOLD:
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
        is_composition_eligible=aggregate < COMPOSITION_THRESHOLD and aggregate >= Decimal("0"),
        state_code=state_code,
        hsn_requirement=hsn_req,
    )


# ─── Composition Scheme ────────────────────────────────────────────────────────

@dataclass
class CompositionInfo:
    is_eligible: bool
    reason: str
    applicable_rate: Decimal | None  # combined CGST+SGST %
    restrictions: list[str]
    return_form: str


def get_composition_info(
    aggregate_turnover: Decimal,
    business_type: str = "trader",  # manufacturer | restaurant | trader | other_services
    has_inter_state_supply: bool = False,
    has_ecommerce_supply: bool = False,
) -> CompositionInfo:
    """
    Check composition scheme eligibility and return applicable rates.
    """
    restrictions = [
        "Cannot make inter-state supplies",
        "Cannot issue tax invoice (use Bill of Supply)",
        "Cannot collect GST from buyer",
        "Cannot claim input tax credit",
        "Cannot supply through e-commerce operator",
    ]

    if aggregate_turnover >= COMPOSITION_THRESHOLD:
        return CompositionInfo(
            is_eligible=False,
            reason=f"Aggregate turnover ₹{aggregate_turnover:,.0f} exceeds ₹50L composition threshold",
            applicable_rate=None,
            restrictions=[],
            return_form="GSTR-3B",
        )

    if has_inter_state_supply:
        return CompositionInfo(
            is_eligible=False,
            reason="Inter-state suppliers cannot opt for composition scheme",
            applicable_rate=None,
            restrictions=[],
            return_form="GSTR-3B",
        )

    if has_ecommerce_supply:
        return CompositionInfo(
            is_eligible=False,
            reason="Suppliers through e-commerce operator cannot use composition scheme",
            applicable_rate=None,
            restrictions=[],
            return_form="GSTR-3B",
        )

    rate = COMPOSITION_RATES.get(business_type, COMPOSITION_RATES["trader"])

    return CompositionInfo(
        is_eligible=True,
        reason=f"Eligible for composition scheme. Turnover ₹{aggregate_turnover:,.0f} < ₹50L",
        applicable_rate=rate,
        restrictions=restrictions,
        return_form="GSTR-4 (quarterly)",
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
    is_traceable: bool  # can be linked to original invoice
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
    """
    Post-supply discount ITC reversal rules (Section 15(3)).
    Discount after supply is deductible only if:
    1. It was agreed upon before/at time of supply, AND
    2. Can be linked to the specific invoice.
    """
    if is_agreed_before_supply and original_invoice_ref:
        # Proportionate ITC reversal required from buyer
        tax = (discount_amount * tax_rate_pct / 100).quantize(Decimal("0.01"))
        breakdown = compute_tax_for_supply(supply_type, discount_amount, tax_rate_pct)
        return CreditNoteITCReversal(
            credit_note_number=credit_note_number,
            original_invoice_ref=original_invoice_ref,
            reversal_igst=breakdown["igst"],
            reversal_cgst=breakdown["cgst"],
            reversal_sgst=breakdown["sgst"],
            reversal_total=breakdown["igst"] + breakdown["cgst"] + breakdown["sgst"],
            is_traceable=True,
            is_allowed=True,
            reason="Discount agreed before supply and traceable to invoice. ITC reversal required from buyer.",
        )
    else:
        return CreditNoteITCReversal(
            credit_note_number=credit_note_number,
            original_invoice_ref=original_invoice_ref,
            reversal_igst=Decimal("0"),
            reversal_cgst=Decimal("0"),
            reversal_sgst=Decimal("0"),
            reversal_total=Decimal("0"),
            is_traceable=False,
            is_allowed=False,
            reason="Post-supply discount not known at time of supply — not deductible from transaction value.",
        )
