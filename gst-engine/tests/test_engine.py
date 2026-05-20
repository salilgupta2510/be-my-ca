"""
Regression test suite for gst-engine.
All cases sourced from known_correct.py — CBIC-derived ground truth.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from decimal import Decimal
from datetime import date

from engine import (
    validate_gstin,
    compute_itc_setoff,
    compute_late_fee,
    compute_aggregate_turnover,
    get_return_due_date,
    check_itc_eligibility,
)
from engine.gstr_compute import compute_gstr4, OutwardInvoiceData, InwardInvoiceData
from engine.rcm import classify_inward_invoice
from tests.known_correct import (
    GSTIN_VALID, GSTIN_INVALID,
    ITC_SETOFF_CASE_1, ITC_SETOFF_CASE_2,
    LATE_FEE_NIL_CASE, LATE_FEE_NONNL_MAXCAP,
    TURNOVER_REG_REQUIRED, TURNOVER_SPECIAL_STATE,
    GSTR4_RESTAURANT_RATE, GSTR4_TRADER_RATE,
    RCM_CASES, ITC_ELIGIBILITY_CASES, DUE_DATE_CASES,
)


# ─── GSTIN Validation ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("gstin", GSTIN_VALID)
def test_gstin_valid(gstin):
    is_valid, err = validate_gstin(gstin)
    assert is_valid, f"Expected valid but got error: {err}"


@pytest.mark.parametrize("gstin,reason", GSTIN_INVALID)
def test_gstin_invalid(gstin, reason):
    is_valid, err = validate_gstin(gstin)
    assert not is_valid, f"Expected invalid for '{gstin}' (reason: {reason})"


# ─── ITC Set-Off ──────────────────────────────────────────────────────────────

def test_itc_setoff_case1():
    c = ITC_SETOFF_CASE_1
    result = compute_itc_setoff(**c["input"])
    exp = c["expected"]
    assert result.igst_credit_used == exp["igst_credit_used"]
    assert result.cgst_credit_used == exp["cgst_credit_used"]
    assert result.sgst_credit_used == exp["sgst_credit_used"]
    assert result.igst_cash_required == exp["igst_cash_required"]
    assert result.cgst_cash_required == exp["cgst_cash_required"]
    assert result.sgst_cash_required == exp["sgst_cash_required"]
    assert result.total_cash_required == exp["total_cash_required"]


def test_itc_setoff_case2_cgst_cannot_offset_sgst():
    c = ITC_SETOFF_CASE_2
    result = compute_itc_setoff(**c["input"])
    exp = c["expected"]
    assert result.cgst_credit_used == exp["cgst_credit_used"]
    assert result.sgst_credit_used == exp["sgst_credit_used"]
    # CGST credit cannot pay SGST liability
    assert result.cgst_cash_required == exp["cgst_cash_required"]
    assert result.sgst_cash_required == exp["sgst_cash_required"]
    assert result.total_cash_required == exp["total_cash_required"]


def test_itc_setoff_zero_liability():
    result = compute_itc_setoff(
        Decimal("5000"), Decimal("3000"), Decimal("3000"),
        Decimal("0"), Decimal("0"), Decimal("0"),
    )
    assert result.total_cash_required == Decimal("0")
    assert result.igst_credit_remaining == Decimal("5000")


# ─── Late Fees ────────────────────────────────────────────────────────────────

def test_late_fee_nil_return():
    c = LATE_FEE_NIL_CASE
    result = compute_late_fee(**c["input"])
    exp = c["expected"]
    assert result.days_late == exp["days_late"]
    assert result.late_fee_cgst == exp["late_fee_cgst"]
    assert result.late_fee_sgst == exp["late_fee_sgst"]
    assert result.late_fee_total == exp["late_fee_total"]


def test_late_fee_nonnl_maxcap():
    c = LATE_FEE_NONNL_MAXCAP
    result = compute_late_fee(**c["input"])
    exp = c["expected"]
    assert result.late_fee_cgst == exp["late_fee_cgst"]
    assert result.late_fee_total == exp["late_fee_total"]


def test_late_fee_zero_when_on_time():
    result = compute_late_fee(
        return_type="GSTR-3B",
        period="2025-01",
        filing_date=date(2025, 2, 19),  # 1 day before due
        is_nil_return=False,
    )
    assert result.days_late == 0
    assert result.late_fee_total == Decimal("0")


# ─── Aggregate Turnover ────────────────────────────────────────────────────────

def test_turnover_registration_required():
    c = TURNOVER_REG_REQUIRED
    result = compute_aggregate_turnover(**c["input"])
    exp = c["expected"]
    assert result.aggregate_turnover == exp["aggregate_turnover"]
    assert result.is_registration_required == exp["is_registration_required"]
    assert result.is_composition_eligible == exp["is_composition_eligible"]


def test_turnover_special_category_state():
    c = TURNOVER_SPECIAL_STATE
    result = compute_aggregate_turnover(**c["input"])
    exp = c["expected"]
    assert result.is_registration_required == exp["is_registration_required"]
    assert result.registration_threshold == exp["registration_threshold"]


# ─── Due Dates ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("case", DUE_DATE_CASES)
def test_due_dates(case):
    result = get_return_due_date(case["period"], case["return_type"])
    assert result == case["expected"], (
        f"{case['return_type']} {case['period']}: expected {case['expected']}, got {result}"
    )


# ─── ITC Eligibility ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("case", ITC_ELIGIBILITY_CASES)
def test_itc_eligibility(case):
    result = check_itc_eligibility(**case["input"])
    assert result.is_eligible == case["expected_eligible"], (
        f"Case '{case['desc']}': expected is_eligible={case['expected_eligible']}, "
        f"got {result.is_eligible}. Reason: {result.blocked_reason}"
    )
    if not case["expected_eligible"] and "expected_reason_contains" in case:
        assert case["expected_reason_contains"].lower() in result.blocked_reason.lower()


# ─── RCM Classification ────────────────────────────────────────────────────────

@pytest.mark.parametrize("case", RCM_CASES)
def test_rcm_classification(case):
    result = classify_inward_invoice(**case["input"])
    assert result.is_rcm == case["expected_is_rcm"]
    if case.get("expected_reason_contains"):
        assert case["expected_reason_contains"].lower() in (result.rcm_reason or "").lower()
    if case.get("expected_blocked_reason"):
        assert result.itc_blocked_reason == case["expected_blocked_reason"]


# ─── GSTR-4 Composition Rate Fix ─────────────────────────────────────────────

def test_gstr4_restaurant_rate():
    c = GSTR4_RESTAURANT_RATE
    outward = [OutwardInvoiceData(
        invoice_type="b2b", period="2025-01",
        taxable_value=c["taxable_value"],
    )]
    result = compute_gstr4(outward, [], "2025-01", business_type=c["business_type"])
    assert Decimal(str(result["composition_tax"])) == c["expected_composition_tax"]
    assert Decimal(str(result["cgst_payable"])) == c["expected_cgst"]
    assert Decimal(str(result["sgst_payable"])) == c["expected_sgst"]


def test_gstr4_trader_rate():
    c = GSTR4_TRADER_RATE
    outward = [OutwardInvoiceData(
        invoice_type="b2b", period="2025-01",
        taxable_value=c["taxable_value"],
    )]
    result = compute_gstr4(outward, [], "2025-01", business_type=c["business_type"])
    assert Decimal(str(result["composition_tax"])) == c["expected_composition_tax"]


def test_gstr4_old_hardcoded_bug_regression():
    """The old returns.py hardcoded COMPOSITION_RATE = 0.01 (1%) for all types.
    Restaurant should be 5% not 1%. This test catches regression to the old bug."""
    outward = [OutwardInvoiceData(
        invoice_type="b2b", period="2025-01",
        taxable_value=Decimal("100000"),
    )]
    result = compute_gstr4(outward, [], "2025-01", business_type="restaurant")
    # Should be ₹5000 (5%), NOT ₹1000 (1%)
    assert Decimal(str(result["composition_tax"])) == Decimal("5000"), (
        "GSTR-4 bug regression: restaurant rate must be 5%, not 1%"
    )
