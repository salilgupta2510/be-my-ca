"""
Known-correct GST computation cases derived from CBIC circulars and official examples.
These are the ground-truth inputs/outputs used as regression anchors.
"""
from datetime import date
from decimal import Decimal

# ─── GSTIN Validation ─────────────────────────────────────────────────────────
GSTIN_VALID = [
    "27AAPFU0939F1ZV",   # Maharashtra, standard
    "29AABCU9603R1ZP",   # Karnataka
    "07AAACR5055K1ZK",   # Delhi
]
GSTIN_INVALID = [
    ("", "required"),
    ("27AAPFU0939F1Z",  "15 characters"),   # 14 chars
    ("INVALIDGSTIN123", "format"),
    ("00AAPFU0939F1ZV", "state code"),      # state "00" not in state_codes
]

# ─── ITC Set-Off (Section 49) ─────────────────────────────────────────────────
# Source: CBIC FAQ on ITC Utilization (2019)
# IGST credit of 10000, CGST=5000, SGST=5000
# Liabilities: IGST=8000, CGST=4000, SGST=4000
ITC_SETOFF_CASE_1 = {
    "input": {
        "igst_credit": Decimal("10000"),
        "cgst_credit": Decimal("5000"),
        "sgst_credit": Decimal("5000"),
        "igst_liability": Decimal("8000"),
        "cgst_liability": Decimal("4000"),
        "sgst_liability": Decimal("4000"),
    },
    "expected": {
        "igst_credit_used": Decimal("10000"),  # 8000 IGST + 2000 → CGST
        "cgst_credit_used": Decimal("2000"),   # remaining CGST liability = 4000-2000=2000
        "sgst_credit_used": Decimal("4000"),
        "igst_cash_required": Decimal("0"),
        "cgst_cash_required": Decimal("0"),
        "sgst_cash_required": Decimal("0"),
        "igst_credit_remaining": Decimal("0"),
        "cgst_credit_remaining": Decimal("3000"),
        "sgst_credit_remaining": Decimal("1000"),
        "total_cash_required": Decimal("0"),
    },
}

# No IGST credit; CGST cannot offset SGST
ITC_SETOFF_CASE_2 = {
    "input": {
        "igst_credit": Decimal("0"),
        "cgst_credit": Decimal("5000"),
        "sgst_credit": Decimal("5000"),
        "igst_liability": Decimal("0"),
        "cgst_liability": Decimal("8000"),
        "sgst_liability": Decimal("8000"),
    },
    "expected": {
        "igst_credit_used": Decimal("0"),
        "cgst_credit_used": Decimal("5000"),
        "sgst_credit_used": Decimal("5000"),
        "igst_cash_required": Decimal("0"),
        "cgst_cash_required": Decimal("3000"),
        "sgst_cash_required": Decimal("3000"),
        "total_cash_required": Decimal("6000"),
    },
}

# ─── Late Fees ────────────────────────────────────────────────────────────────
# GSTR-3B nil return, 10 days late, turnover < ₹1.5Cr
# Daily = ₹10 each act → ₹100 CGST + ₹100 SGST = ₹200 total (within ₹1000 cap)
LATE_FEE_NIL_CASE = {
    "input": {
        "return_type": "GSTR-3B",
        "period": "2025-01",
        "filing_date": date(2025, 3, 2),   # 20 Feb due + 10 days
        "is_nil_return": True,
        "annual_turnover": Decimal("10000000"),  # ₹1 Cr → slab 1 max ₹2000
    },
    "expected": {
        "days_late": 10,
        "late_fee_cgst": Decimal("100"),
        "late_fee_sgst": Decimal("100"),
        "late_fee_total": Decimal("200"),
    },
}

# Non-nil, 50 days late, turnover > ₹5Cr → ₹25/day each, max ₹1000 each
LATE_FEE_NONNL_MAXCAP = {
    "input": {
        "return_type": "GSTR-1",
        "period": "2025-01",
        "filing_date": date(2025, 4, 2),  # 11 Feb due + 50 days
        "is_nil_return": False,
        "annual_turnover": Decimal("100000000"),  # ₹10 Cr → max ₹10000 total
    },
    "expected": {
        "days_late": 50,
        "late_fee_cgst": Decimal("1000"),    # min(50*25=1250, 1000 cap)
        "late_fee_sgst": Decimal("1000"),
        "late_fee_total": Decimal("2000"),
    },
}

# ─── Aggregate Turnover ────────────────────────────────────────────────────────
# Maharashtra (27) — normal threshold ₹20L
TURNOVER_REG_REQUIRED = {
    "input": {
        "taxable_value": Decimal("1500000"),
        "exempt_value": Decimal("600000"),
        "export_value": Decimal("0"),
        "inter_state_value": Decimal("0"),
        "state_code": "27",
    },
    "expected": {
        "aggregate_turnover": Decimal("2100000"),
        "is_registration_required": True,
        "is_composition_eligible": True,  # < ₹50L
    },
}

# Special category state (J&K = "01") — threshold ₹10L
TURNOVER_SPECIAL_STATE = {
    "input": {
        "taxable_value": Decimal("1200000"),
        "exempt_value": Decimal("0"),
        "export_value": Decimal("0"),
        "inter_state_value": Decimal("0"),
        "state_code": "01",
    },
    "expected": {
        "is_registration_required": True,
        "registration_threshold": Decimal("1000000"),
    },
}

# ─── Composition Rates ────────────────────────────────────────────────────────
# GSTR-4: restaurant @ 5% total (2.5% CGST + 2.5% SGST)
GSTR4_RESTAURANT_RATE = {
    "business_type": "restaurant",
    "taxable_value": Decimal("100000"),
    "expected_composition_tax": Decimal("5000"),   # 5% of 1L
    "expected_cgst": Decimal("2500"),
    "expected_sgst": Decimal("2500"),
}

# GSTR-4: trader @ 1%
GSTR4_TRADER_RATE = {
    "business_type": "trader",
    "taxable_value": Decimal("100000"),
    "expected_composition_tax": Decimal("1000"),   # 1% of 1L
    "expected_cgst": Decimal("500"),
    "expected_sgst": Decimal("500"),
}

# ─── RCM Classification ────────────────────────────────────────────────────────
RCM_CASES = [
    {
        "input": {"supplier_gstin": None, "hsn_code": "9965", "supplier_name": "Fast Freight Co"},
        "expected_is_rcm": True,
        "expected_reason_contains": "GTA",
    },
    {
        "input": {"supplier_gstin": "27AAPFU0939F1ZV", "hsn_code": "9982", "supplier_name": "Legal Eagles LLP"},
        "expected_is_rcm": True,
        "expected_reason_contains": "Legal",
    },
    {
        "input": {"supplier_gstin": "29AABCU9603R1ZP", "hsn_code": "8517", "supplier_name": "Tech Supplies Ltd"},
        "expected_is_rcm": False,
    },
    {
        # GSTIN-registered local car dealer — not RCM, but ITC is blocked (S.17(5))
        "input": {"supplier_gstin": "27AAPFU0939F1ZV", "hsn_code": "8703", "supplier_name": "City Motors"},
        "expected_is_rcm": False,
        "expected_blocked_reason": "motor_vehicle",
    },
]

# ─── ITC Eligibility ─────────────────────────────────────────────────────────
ITC_ELIGIBILITY_CASES = [
    {
        "desc": "fresh invoice — eligible",
        "input": {
            "invoice_id": "1", "supplier_name": "Supplier A", "invoice_number": "INV001",
            "invoice_date": date(2025, 1, 15),
            "igst": Decimal("1800"), "cgst": Decimal("0"), "sgst": Decimal("0"),
            "itc_category": None, "is_rcm": False,
            "check_date": date(2025, 6, 1),
        },
        "expected_eligible": True,
    },
    {
        "desc": "time-barred invoice — blocked",
        "input": {
            "invoice_id": "2", "supplier_name": "Old Supplier", "invoice_number": "INV002",
            "invoice_date": date(2023, 1, 1),
            "igst": Decimal("1000"), "cgst": Decimal("0"), "sgst": Decimal("0"),
            "itc_category": None, "is_rcm": False,
            "check_date": date(2025, 6, 1),  # > 1 year from invoice date
        },
        "expected_eligible": False,
        "expected_reason_contains": "time-barred",
    },
    {
        "desc": "motor vehicle — Section 17(5) blocked",
        "input": {
            "invoice_id": "3", "supplier_name": "Car Dealer", "invoice_number": "INV003",
            "invoice_date": date(2025, 1, 1),
            "igst": Decimal("100000"), "cgst": Decimal("0"), "sgst": Decimal("0"),
            "itc_category": "motor_vehicle", "is_rcm": False,
            "check_date": date(2025, 3, 1),
        },
        "expected_eligible": False,
        "expected_reason_contains": "17(5)",
    },
]

# ─── Due Dates ────────────────────────────────────────────────────────────────
DUE_DATE_CASES = [
    {"return_type": "gstr1",  "period": "2025-01", "expected": date(2025, 2, 11)},
    {"return_type": "gstr3b", "period": "2025-01", "expected": date(2025, 2, 20)},
    {"return_type": "gstr4",  "period": "2025-03", "expected": date(2025, 4, 18)},
    {"return_type": "gstr9",  "period": "2024-25", "expected": date(2025, 12, 31)},
]
