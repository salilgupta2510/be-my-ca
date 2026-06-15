"""
ITR computation engine — tax slab, deductions, old vs new regime comparison.

Supported assessment years:
  AY 2025-26 (FY 2024-25) — filing deadline Jul 31, 2025
  AY 2026-27 (FY 2025-26) — Budget 2025 slabs (new regime restructured)

References:
  Finance Act 2024 (Budget 2024) — AY 2025-26 rules
  Finance Act 2025 (Budget 2025) — AY 2026-27 rules
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.schemas.itr import (
    Form16Data,
    RegimeResult,
    RegimeComparison,
    SlabBreakdown,
)

# ── Tax slab definitions ──────────────────────────────────────────────────────
# Each slab: (upper_limit_inclusive, rate_as_decimal)
# None as upper_limit = top slab (no ceiling)

_OLD_SLABS: dict[str, list[tuple[Decimal | None, Decimal]]] = {
    # Normal: < 60 yrs
    "normal": [
        (Decimal("250000"), Decimal("0")),
        (Decimal("500000"), Decimal("0.05")),
        (Decimal("1000000"), Decimal("0.20")),
        (None, Decimal("0.30")),
    ],
    # Senior citizen: 60–79 yrs
    "senior": [
        (Decimal("300000"), Decimal("0")),
        (Decimal("500000"), Decimal("0.05")),
        (Decimal("1000000"), Decimal("0.20")),
        (None, Decimal("0.30")),
    ],
    # Super senior: 80+ yrs
    "super_senior": [
        (Decimal("500000"), Decimal("0")),
        (Decimal("1000000"), Decimal("0.20")),
        (None, Decimal("0.30")),
    ],
}

# New regime slabs — AY 2025-26 (FY 2024-25, Budget 2023/2024)
_NEW_SLABS_AY2526: list[tuple[Decimal | None, Decimal]] = [
    (Decimal("300000"), Decimal("0")),
    (Decimal("600000"), Decimal("0.05")),
    (Decimal("900000"), Decimal("0.10")),
    (Decimal("1200000"), Decimal("0.15")),
    (Decimal("1500000"), Decimal("0.20")),
    (None, Decimal("0.30")),
]

# New regime slabs — AY 2026-27 (FY 2025-26, Budget 2025)
_NEW_SLABS_AY2627: list[tuple[Decimal | None, Decimal]] = [
    (Decimal("400000"), Decimal("0")),
    (Decimal("800000"), Decimal("0.05")),
    (Decimal("1200000"), Decimal("0.10")),
    (Decimal("1600000"), Decimal("0.15")),
    (Decimal("2000000"), Decimal("0.20")),
    (Decimal("2400000"), Decimal("0.25")),
    (None, Decimal("0.30")),
]

# Standard deduction by regime & AY
_STD_DEDUCTION: dict[str, dict[str, Decimal]] = {
    "old": {
        "2025-26": Decimal("50000"),
        "2026-27": Decimal("50000"),
    },
    "new": {
        "2025-26": Decimal("75000"),   # raised in Budget 2024
        "2026-27": Decimal("75000"),
    },
}

# 87A rebate: (income_ceiling, max_rebate)
_REBATE_87A: dict[str, dict[str, tuple[Decimal, Decimal]]] = {
    "old": {
        "2025-26": (Decimal("500000"), Decimal("12500")),
        "2026-27": (Decimal("500000"), Decimal("12500")),
    },
    "new": {
        "2025-26": (Decimal("700000"), Decimal("25000")),
        "2026-27": (Decimal("1200000"), Decimal("60000")),  # Budget 2025 — 12L limit
    },
}

# Surcharge thresholds (income → surcharge rate)
_SURCHARGE_BRACKETS = [
    (Decimal("5000000"),  Decimal("0")),
    (Decimal("10000000"), Decimal("0.10")),
    (Decimal("20000000"), Decimal("0.15")),
    (Decimal("50000000"), Decimal("0.25")),
    (None,                Decimal("0.37")),   # old regime only; new caps at 0.25
]
_NEW_REGIME_MAX_SURCHARGE = Decimal("0.25")


def _rupees(v: Decimal) -> Decimal:
    return v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _compute_slab_tax(
    income: Decimal,
    slabs: list[tuple[Decimal | None, Decimal]],
) -> tuple[Decimal, list[SlabBreakdown]]:
    """Returns (total_tax, per_slab_breakdown)."""
    tax = Decimal("0")
    breakdown: list[SlabBreakdown] = []
    prev = Decimal("0")

    for upper, rate in slabs:
        if income <= prev:
            break
        ceil = upper if upper is not None else income
        taxable = min(income, ceil) - prev
        if taxable <= 0:
            prev = ceil if upper is not None else income
            continue
        slab_tax = _rupees(taxable * rate)
        if rate > 0 or upper is None:
            breakdown.append(SlabBreakdown(
                from_amount=prev,
                to_amount=min(income, ceil) if upper is not None else income,
                rate_pct=float(rate * 100),
                tax=slab_tax,
            ))
        tax += slab_tax
        prev = ceil if upper is not None else income

    return tax, breakdown


def _compute_surcharge(income: Decimal, base_tax: Decimal, regime: str) -> Decimal:
    rate = Decimal("0")
    for ceiling, r in _SURCHARGE_BRACKETS:
        if ceiling is None or income > ceiling:
            rate = r
        else:
            break
    if regime == "new":
        rate = min(rate, _NEW_REGIME_MAX_SURCHARGE)
    return _rupees(base_tax * rate)


def _compute_87a(income: Decimal, tax: Decimal, regime: str, ay: str) -> Decimal:
    ceiling, max_rebate = _REBATE_87A[regime][ay]
    if income <= ceiling:
        return min(tax, max_rebate)
    return Decimal("0")


def _cess(amount: Decimal) -> Decimal:
    return _rupees(amount * Decimal("0.04"))


def _old_regime_category(age: int) -> str:
    if age >= 80:
        return "super_senior"
    if age >= 60:
        return "senior"
    return "normal"


# ── Deduction caps ────────────────────────────────────────────────────────────

_80CCE_CAP = Decimal("150000")   # aggregate of 80C + 80CCC + 80CCD(1)
_80CCD_1B_CAP = Decimal("50000")
_80D_CAP_NORMAL = Decimal("25000")
_80D_CAP_SENIOR = Decimal("50000")
_80TTA_CAP = Decimal("10000")
_80TTB_CAP = Decimal("50000")


def _compute_old_regime(
    form16: Form16Data,
    additional_interest: Decimal,
    additional_rental: Decimal,
    additional_other: Decimal,
    employer_nps: Decimal,
    age: int,
    ay: str,
) -> RegimeResult:
    pb = form16.part_b
    pa = form16.part_a

    # Step 1: Gross salary
    gross = pb.gross_salary

    # Step 2: Sec 10 exemptions (HRA, LTA, others)
    sec10 = pb.hra_exempt_10_13a + pb.lta_exempt_10_5 + pb.other_exempt_10
    net_salary = gross - sec10

    # Step 3: Deductions u/s 16
    std_ded = _STD_DEDUCTION["old"][ay]
    pt = pb.professional_tax_16_iii
    income_from_salary = net_salary - std_ded - pt

    # Step 4: Additional income
    add_income = additional_interest + additional_rental + additional_other
    gross_total_income = income_from_salary + add_income

    # Step 5: Chapter VI-A — capped per section
    ded = pb.deductions
    sec_80cce = min(ded.sec_80c + ded.sec_80ccc + ded.sec_80ccd_1, _80CCE_CAP)
    sec_80ccd_1b = min(ded.sec_80ccd_1b, _80CCD_1B_CAP)
    # 80CCD(2) employer NPS — also allowed in old, no cap beyond 10% basic
    # We take the value from Form16 or override
    eff_employer_nps = employer_nps or ded.sec_80ccd_2
    d_cap = _80D_CAP_SENIOR if age >= 60 else _80D_CAP_NORMAL
    sec_80d = min(ded.sec_80d, d_cap * 2)    # self + parents each capped
    sec_80e = ded.sec_80e                     # uncapped
    sec_80g = ded.sec_80g                     # subject to qualifying amount, take as-is
    tta_ttb = min(ded.sec_80ttb, _80TTB_CAP) if age >= 60 else min(ded.sec_80tta, _80TTA_CAP)
    sec_80u = ded.sec_80u
    sec_80dd = ded.sec_80dd
    sec_80ddb = ded.sec_80ddb

    total_via = (
        sec_80cce + sec_80ccd_1b + eff_employer_nps
        + sec_80d + sec_80e + sec_80g + tta_ttb
        + sec_80u + sec_80dd + sec_80ddb
    )
    total_via = min(total_via, gross_total_income)   # can't exceed GTI

    taxable = _rupees(max(gross_total_income - total_via, Decimal("0")))

    # Step 6: Tax on taxable income
    cat = _old_regime_category(age)
    base_tax, slab_breakdown = _compute_slab_tax(taxable, _OLD_SLABS[cat])

    # Step 7: 87A rebate
    rebate = _compute_87a(taxable, base_tax, "old", ay)
    after_rebate = _rupees(base_tax - rebate)

    # Step 8: Surcharge
    surcharge = _compute_surcharge(taxable, after_rebate, "old")

    # Step 9: Cess
    cess = _cess(after_rebate + surcharge)

    total_tax = after_rebate + surcharge + cess

    # Step 10: Balance
    tds = pa.total_tds_deducted or pb.tds_by_this_employer
    balance = _rupees(total_tax - tds)

    applicable_deductions: dict[str, Decimal] = {}
    if sec_80cce:      applicable_deductions["80C/CCC/CCD(1)"] = sec_80cce
    if sec_80ccd_1b:   applicable_deductions["80CCD(1B) NPS"] = sec_80ccd_1b
    if eff_employer_nps: applicable_deductions["80CCD(2) Employer NPS"] = eff_employer_nps
    if sec_80d:        applicable_deductions["80D Health Insurance"] = sec_80d
    if sec_80e:        applicable_deductions["80E Education Loan"] = sec_80e
    if sec_80g:        applicable_deductions["80G Donations"] = sec_80g
    if tta_ttb:        applicable_deductions["80TTA/TTB Interest"] = tta_ttb
    if sec_80u:        applicable_deductions["80U Disability"] = sec_80u

    return RegimeResult(
        regime="old",
        assessment_year=ay,
        gross_salary=gross,
        sec10_exemptions=sec10,
        net_salary=net_salary,
        standard_deduction=std_ded,
        professional_tax=pt,
        employer_nps_80ccd2=eff_employer_nps,
        income_from_salary=income_from_salary,
        additional_income=add_income,
        gross_total_income=gross_total_income,
        chapter_via_deductions=total_via,
        total_taxable_income=taxable,
        tax_on_income=base_tax,
        rebate_87a=rebate,
        tax_after_rebate=after_rebate,
        surcharge=surcharge,
        cess=cess,
        total_tax=total_tax,
        tds_deducted=tds,
        balance_payable=balance,
        applicable_deductions=applicable_deductions,
        slab_breakdown=slab_breakdown,
    )


def _compute_new_regime(
    form16: Form16Data,
    additional_interest: Decimal,
    additional_rental: Decimal,
    additional_other: Decimal,
    employer_nps: Decimal,
    age: int,
    ay: str,
) -> RegimeResult:
    pb = form16.part_b
    pa = form16.part_a

    # Step 1: Gross salary — no Sec 10 HRA/LTA exemptions in new regime
    gross = pb.gross_salary

    # Step 2: Deductions u/s 16 (SD + PT still allowed)
    std_ded = _STD_DEDUCTION["new"][ay]
    pt = pb.professional_tax_16_iii
    # 80CCD(2) employer NPS — allowed in new regime too
    eff_employer_nps = employer_nps or pb.deductions.sec_80ccd_2
    income_from_salary = gross - std_ded - pt - eff_employer_nps

    # Step 3: Additional income
    add_income = additional_interest + additional_rental + additional_other
    taxable = _rupees(max(income_from_salary + add_income, Decimal("0")))

    # Step 4: Slab tax (no age differentiation in new regime)
    slabs = _NEW_SLABS_AY2526 if ay == "2025-26" else _NEW_SLABS_AY2627
    base_tax, slab_breakdown = _compute_slab_tax(taxable, slabs)

    # Step 5: 87A rebate
    rebate = _compute_87a(taxable, base_tax, "new", ay)
    after_rebate = _rupees(base_tax - rebate)

    # Step 6: Surcharge
    surcharge = _compute_surcharge(taxable, after_rebate, "new")

    # Step 7: Cess
    cess = _cess(after_rebate + surcharge)

    total_tax = after_rebate + surcharge + cess

    # Step 8: Balance
    tds = pa.total_tds_deducted or pb.tds_by_this_employer
    balance = _rupees(total_tax - tds)

    applicable_deductions: dict[str, Decimal] = {}
    if eff_employer_nps:
        applicable_deductions["80CCD(2) Employer NPS"] = eff_employer_nps

    return RegimeResult(
        regime="new",
        assessment_year=ay,
        gross_salary=gross,
        sec10_exemptions=Decimal("0"),       # not applicable
        net_salary=gross,                    # no sec10 in new
        standard_deduction=std_ded,
        professional_tax=pt,
        employer_nps_80ccd2=eff_employer_nps,
        income_from_salary=income_from_salary,
        additional_income=add_income,
        gross_total_income=income_from_salary + add_income,
        chapter_via_deductions=Decimal("0"),  # not applicable
        total_taxable_income=taxable,
        tax_on_income=base_tax,
        rebate_87a=rebate,
        tax_after_rebate=after_rebate,
        surcharge=surcharge,
        cess=cess,
        total_tax=total_tax,
        tds_deducted=tds,
        balance_payable=balance,
        applicable_deductions=applicable_deductions,
        slab_breakdown=slab_breakdown,
    )


def _key_factors(
    old: RegimeResult,
    new: RegimeResult,
    form16: Form16Data,
    recommended: str,
) -> list[str]:
    pb = form16.part_b
    factors: list[str] = []

    if pb.hra_exempt_10_13a > 0:
        factors.append(
            f"HRA exemption ₹{int(pb.hra_exempt_10_13a):,} saves tax only in old regime"
        )
    if pb.lta_exempt_10_5 > 0:
        factors.append(
            f"LTA exemption ₹{int(pb.lta_exempt_10_5):,} saves tax only in old regime"
        )
    if old.chapter_via_deductions > 0:
        factors.append(
            f"Chapter VI-A deductions ₹{int(old.chapter_via_deductions):,} available only in old regime"
        )
    std_diff = new.standard_deduction - old.standard_deduction
    if std_diff > 0:
        factors.append(
            f"New regime gives ₹{int(std_diff):,} higher standard deduction"
        )
    if new.employer_nps_80ccd2 > 0:
        factors.append(
            f"Employer NPS ₹{int(new.employer_nps_80ccd2):,} deductible in both regimes"
        )

    diff = abs(old.total_tax - new.total_tax)
    if recommended == "new":
        factors.append(
            f"New regime rates are lower for this income level — saves ₹{int(diff):,}"
        )
    else:
        factors.append(
            f"Old regime deductions outweigh rate benefit — saves ₹{int(diff):,}"
        )

    # Cliff warning for new regime
    ceiling, _ = _REBATE_87A["new"][old.assessment_year]
    if new.total_taxable_income > ceiling and new.total_taxable_income <= ceiling + Decimal("200000"):
        factors.append(
            f"⚠ Income slightly above ₹{int(ceiling/100000)}L rebate cliff — "
            "verify with CA if restructuring is possible"
        )

    return factors


def compare_regimes(
    form16: Form16Data,
    additional_interest: Decimal = Decimal("0"),
    additional_rental: Decimal = Decimal("0"),
    additional_other: Decimal = Decimal("0"),
    employer_nps: Decimal = Decimal("0"),
    age: int = 30,
    ay: str = "2025-26",
) -> RegimeComparison:
    old = _compute_old_regime(
        form16, additional_interest, additional_rental, additional_other,
        employer_nps, age, ay,
    )
    new = _compute_new_regime(
        form16, additional_interest, additional_rental, additional_other,
        employer_nps, age, ay,
    )

    recommended = "old" if old.total_tax <= new.total_tax else "new"
    savings = abs(old.total_tax - new.total_tax)
    factors = _key_factors(old, new, form16, recommended)

    return RegimeComparison(
        old_regime=old,
        new_regime=new,
        recommended=recommended,
        tax_difference=new.total_tax - old.total_tax,   # negative = old costs less
        savings=savings,
        key_factors=factors,
        financial_year=f"20{ay[:2]}-{int(ay[:2])+1}",
        assessment_year=ay,
    )
