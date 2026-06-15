"""
AIS vs Form 16 vs Capital Gains reconciler.

Compares income declared / parsed across all sources and flags discrepancies
that could trigger IT department notices post-filing.

Checks:
  1. TDS from salary     — Form 16 Part A vs AIS salary_tds
  2. Interest income     — AIS interest vs declared additional_income.interest_income
  3. Dividend income     — AIS dividends vs declared (flagged if undeclared)
  4. Capital gains       — AIS securities/MF sale value vs CG CSV total sell amounts
  5. Advance tax paid    — AIS advance tax vs what we'd expect (informational)

Severity:
  info    — delta within tolerance (₹500), matches expected
  warning — delta > ₹1,000 and < ₹50,000 (undeclared income)
  error   — delta > ₹50,000 or TDS mismatch > ₹500 (high notice risk)
"""
from __future__ import annotations

from decimal import Decimal

from app.schemas.itr import (
    AISData,
    AdditionalIncome,
    CapitalGainsSummary,
    Form16Data,
    ReconciliationItem,
    ReconciliationReport,
)

_TDS_TOLERANCE = Decimal("500")       # small rounding differences ignored
_INCOME_TOLERANCE = Decimal("1000")   # delta below this → info, not warning
_INCOME_HIGH = Decimal("50000")       # delta above this → error


def _item(
    category: str,
    description: str,
    form16: Decimal | None,
    ais: Decimal | None,
    declared: Decimal | None,
    severity: str,
    action: str,
) -> ReconciliationItem:
    # delta = ais (what IT dept sees) minus what user declared
    ais_val = ais or Decimal("0")
    declared_val = declared if declared is not None else (form16 or Decimal("0"))
    delta = ais_val - declared_val
    return ReconciliationItem(
        category=category,
        description=description,
        form16_amount=form16,
        ais_amount=ais,
        declared_amount=declared,
        delta=delta,
        severity=severity,
        action=action,
    )


def _sev(delta: Decimal, is_tds: bool = False) -> str:
    abs_delta = abs(delta)
    if is_tds:
        return "error" if abs_delta > _TDS_TOLERANCE else "info"
    if abs_delta <= _INCOME_TOLERANCE:
        return "info"
    if abs_delta >= _INCOME_HIGH:
        return "error"
    return "warning"


def reconcile(
    form16: Form16Data,
    ais: AISData,
    additional_income: AdditionalIncome,
    capital_gains: CapitalGainsSummary | None = None,
) -> ReconciliationReport:
    items: list[ReconciliationItem] = []

    # ── 1. TDS from salary ────────────────────────────────────────────────────
    f16_tds = form16.part_b.total_tds or form16.part_a.total_tds_deducted
    ais_tds = ais.total_tds_from_salary

    if ais_tds > 0 or f16_tds > 0:
        delta = ais_tds - f16_tds
        sev = _sev(delta, is_tds=True)
        if sev == "info":
            action = "TDS matches. No action needed."
        elif delta > 0:
            action = (
                f"AIS shows ₹{delta:,.0f} more TDS than Form 16. "
                "Contact employer — may be missing TDS challan in Form 16, or employer correction needed."
            )
        else:
            action = (
                f"Form 16 shows ₹{abs(delta):,.0f} more TDS than AIS. "
                "Verify TDS deposit with employer before filing — portal will only allow credit for AIS amount."
            )
        items.append(_item(
            "tds_salary", "TDS from salary (Form 16 vs AIS)",
            f16_tds, ais_tds, None, sev, action,
        ))

    # ── 2. Interest income ────────────────────────────────────────────────────
    ais_interest = ais.total_interest_income
    declared_interest = additional_income.interest_income

    if ais_interest > _INCOME_TOLERANCE or declared_interest > 0:
        delta = ais_interest - declared_interest
        sev = _sev(delta)
        if sev == "info":
            action = "Interest income matches AIS. OK to file."
        elif delta > 0:
            action = (
                f"AIS shows ₹{ais_interest:,.0f} interest income but you declared ₹{declared_interest:,.0f}. "
                f"Include the full ₹{ais_interest:,.0f} under 'Income from Other Sources' to avoid 143(1) mismatch."
            )
        else:
            action = "Declared interest exceeds AIS — verify with bank statements before filing."
        items.append(_item(
            "interest", "Interest income (AIS vs declared)",
            None, ais_interest, declared_interest, sev, action,
        ))

    # ── 3. Dividend income ────────────────────────────────────────────────────
    ais_div = ais.total_dividend_income
    declared_div = additional_income.other_income  # dividends go here for now

    if ais_div > _INCOME_TOLERANCE:
        delta = ais_div - declared_div
        sev = _sev(delta)
        if sev == "info":
            action = "Dividend income appears covered in declared other income."
        else:
            action = (
                f"AIS shows ₹{ais_div:,.0f} dividend income. "
                "Declare under 'Income from Other Sources → Dividends' in ITR. "
                "Dividends are fully taxable at slab rate from FY 2020-21."
            )
        items.append(_item(
            "dividend", "Dividend income (AIS vs declared)",
            None, ais_div, declared_div, sev, action,
        ))

    # ── 4. Capital gains — AIS sale value vs CG CSV ───────────────────────────
    ais_sec_sale = ais.total_securities_sale_value
    ais_mf_sale = ais.total_mf_redemption_value
    ais_total_sale = ais_sec_sale + ais_mf_sale

    if ais_total_sale > 0:
        if capital_gains is None:
            items.append(ReconciliationItem(
                category="capital_gains",
                description="Securities/MF sales in AIS — no CG CSV uploaded",
                ais_amount=ais_total_sale,
                delta=ais_total_sale,
                severity="error",
                action=(
                    f"AIS shows ₹{ais_total_sale:,.0f} in securities/MF sale proceeds. "
                    "Upload your broker P&L CSV via /itr/capital-gains/upload to declare capital gains. "
                    "Undeclared CG is a common cause of 143(1) demand notices."
                ),
            ))
        else:
            cg_sell = sum(
                t.sell_amount for t in capital_gains.trades
            )
            delta = ais_total_sale - cg_sell
            sev = _sev(delta)
            if sev == "info":
                action = "CG sale values match AIS. OK to file."
            elif delta > 0:
                action = (
                    f"AIS shows ₹{delta:,.0f} more sale proceeds than your CG CSV. "
                    "Check for missing trades — possibly from another demat account."
                )
            else:
                action = (
                    f"CG CSV shows ₹{abs(delta):,.0f} more proceeds than AIS. "
                    "Verify with broker — some trades may not yet be reported in AIS."
                )
            items.append(_item(
                "capital_gains", "Securities/MF sale value (AIS vs CG CSV)",
                None, ais_total_sale, cg_sell, sev, action,
            ))

    # ── 5. TDS from others (interest, dividends) ──────────────────────────────
    if ais.total_tds_from_others > _TDS_TOLERANCE:
        items.append(ReconciliationItem(
            category="tds_other",
            description=f"TDS on non-salary income (interest/dividends) — ₹{ais.total_tds_from_others:,.0f} in AIS",
            ais_amount=ais.total_tds_from_others,
            delta=Decimal("0"),
            severity="info",
            action=(
                f"Claim ₹{ais.total_tds_from_others:,.0f} TDS credit in Schedule TDS2 of ITR. "
                "This reduces your net tax payable."
            ),
        ))

    # ── Summary ───────────────────────────────────────────────────────────────
    errors = [i for i in items if i.severity == "error"]
    warnings = [i for i in items if i.severity == "warning"]
    ok = [i for i in items if i.severity == "info"]

    if errors:
        filing_risk = "high"
    elif warnings:
        filing_risk = "medium"
    else:
        filing_risk = "low"

    undeclared = sum(
        i.delta for i in items
        if i.delta > 0 and i.category != "tds_salary" and i.category != "tds_other"
    )

    recommendations: list[str] = []
    if filing_risk == "high":
        recommendations.append(
            "Resolve all ERROR items before filing — these will likely trigger a 143(1) demand notice."
        )
    if filing_risk == "medium":
        recommendations.append(
            "Declare all WARNING items before filing — undeclared income in AIS commonly triggers 143(1) notices."
        )
    if ais.total_interest_income > _INCOME_HIGH:
        recommendations.append(
            "Large interest income in AIS — ensure Form 15G/15H was not submitted if TDS was required."
        )
    if capital_gains is None and ais_total_sale > 0:
        recommendations.append("Upload broker P&L CSV to compute capital gains before generating ITR XML.")
    if filing_risk == "low":
        recommendations.append("No major discrepancies. Proceed to ITR XML generation.")

    ay = ais.assessment_year or form16.part_a.assessment_year or "2025-26"

    return ReconciliationReport(
        items=items,
        filing_risk=filing_risk,
        undeclared_income=undeclared,
        total_discrepancies=len(errors) + len(warnings),
        ok_count=len(ok),
        recommendations=recommendations,
        assessment_year=ay,
    )
