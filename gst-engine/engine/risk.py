"""
Notice Shield risk scoring engine.
Scores 0-100 based on declared income vs actual financial activity.
"""
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class RiskFactor:
    factor: str
    score: int
    weight: float
    description: str
    advice: str
    triggered: bool = False


@dataclass
class RiskReport:
    overall_score: int
    level: str  # low / medium / high / critical
    factors: list[dict] = field(default_factory=list)

    @property
    def level_color(self) -> str:
        return {"low": "green", "medium": "yellow", "high": "orange", "critical": "red"}[self.level]


def _level(score: int) -> str:
    if score < 30:
        return "low"
    elif score < 55:
        return "medium"
    elif score < 75:
        return "high"
    return "critical"


def compute_risk_score(
    declared_income: Decimal,
    total_cash_deposits: Decimal,
    total_high_value_purchases: Decimal,
    total_credits: Decimal,
    gst_mismatch_count: int,
    itc_reversal_risk_amount: Decimal,
    has_foreign_transactions: bool = False,
) -> RiskReport:
    factors: list[RiskFactor] = [
        RiskFactor(
            factor="cash_transactions", score=0, weight=0.30, description="",
            advice="Keep cash deposits under 10% of declared income. Use digital payments.",
        ),
        RiskFactor(
            factor="high_value_purchases", score=0, weight=0.25, description="",
            advice="Ensure high-value purchases (vehicle, property, jewelry) are reflected in ITR.",
        ),
        RiskFactor(
            factor="income_credit_gap", score=0, weight=0.20, description="",
            advice="Total bank credits significantly exceed declared income. Reconcile sources.",
        ),
        RiskFactor(
            factor="gst_mismatches", score=0, weight=0.15, description="",
            advice="Resolve GST mismatches to avoid ITC reversal notices.",
        ),
        RiskFactor(
            factor="itc_reversal_risk", score=0, weight=0.10, description="",
            advice="Vendors with pending GSTR-1 filings may trigger ITC reversal demand.",
        ),
    ]

    income = float(declared_income) or 1

    cash_pct = float(total_cash_deposits) / income * 100
    if cash_pct > 20:
        factors[0].score = 90; factors[0].triggered = True
        factors[0].description = f"Cash deposits ₹{total_cash_deposits:,.0f} = {cash_pct:.1f}% of income. Exceeds 20% threshold."
    elif cash_pct > 10:
        factors[0].score = 60; factors[0].triggered = True
        factors[0].description = f"Cash deposits ₹{total_cash_deposits:,.0f} = {cash_pct:.1f}% of income. Above 10% threshold."
    else:
        factors[0].score = 10
        factors[0].description = f"Cash deposits within safe limits ({cash_pct:.1f}% of income)."

    hvp_pct = float(total_high_value_purchases) / income * 100
    if hvp_pct > 50:
        factors[1].score = 85; factors[1].triggered = True
        factors[1].description = f"High-value purchases ₹{total_high_value_purchases:,.0f} = {hvp_pct:.1f}% of declared income."
    elif hvp_pct > 20:
        factors[1].score = 50; factors[1].triggered = True
        factors[1].description = f"High-value purchases at {hvp_pct:.1f}% of income. Monitor."
    else:
        factors[1].score = 5

    credit_pct = float(total_credits) / income * 100
    if credit_pct > 150:
        factors[2].score = 80; factors[2].triggered = True
        factors[2].description = f"Bank credits ₹{total_credits:,.0f} are {credit_pct:.0f}% of declared income."
    elif credit_pct > 110:
        factors[2].score = 45; factors[2].triggered = True
        factors[2].description = f"Bank credits slightly exceed declared income ({credit_pct:.0f}%)."
    else:
        factors[2].score = 10

    if gst_mismatch_count > 20:
        factors[3].score = 80; factors[3].triggered = True
        factors[3].description = f"{gst_mismatch_count} unresolved GST mismatches."
    elif gst_mismatch_count > 5:
        factors[3].score = 45; factors[3].triggered = True
        factors[3].description = f"{gst_mismatch_count} GST mismatches need attention."
    else:
        factors[3].score = 5

    itc_pct = float(itc_reversal_risk_amount) / income * 100
    if itc_pct > 5:
        factors[4].score = 70; factors[4].triggered = True
        factors[4].description = f"₹{itc_reversal_risk_amount:,.0f} ITC at risk from non-filing vendors."
    else:
        factors[4].score = 10

    overall = min(100, max(0, int(sum(f.score * f.weight for f in factors))))
    return RiskReport(
        overall_score=overall,
        level=_level(overall),
        factors=[
            {"factor": f.factor, "score": f.score, "triggered": f.triggered,
             "description": f.description, "advice": f.advice}
            for f in factors
        ],
    )
