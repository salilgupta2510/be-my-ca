"""
ITR-related Pydantic schemas.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Form16PartA(BaseModel):
    employer_name: str | None = None
    employer_tan: str | None = None
    employer_pan: str | None = None
    employee_name: str | None = None
    employee_pan: str | None = None
    employee_designation: str | None = None
    financial_year: str | None = None        # e.g. "2024-25"
    assessment_year: str | None = None       # e.g. "2025-26"
    period_from: str | None = None           # "DD/MM/YYYY"
    period_to: str | None = None
    tds_q1: Decimal = Decimal("0")
    tds_q2: Decimal = Decimal("0")
    tds_q3: Decimal = Decimal("0")
    tds_q4: Decimal = Decimal("0")
    total_tds_deducted: Decimal = Decimal("0")
    total_tds_deposited: Decimal = Decimal("0")


class Form16Deductions(BaseModel):
    """Chapter VI-A deductions as reported in Part B."""
    sec_80c: Decimal = Decimal("0")          # PF, ELSS, LIC, PPF, home loan principal
    sec_80ccc: Decimal = Decimal("0")        # pension fund
    sec_80ccd_1: Decimal = Decimal("0")      # NPS employee (within 1.5L 80CCE limit)
    sec_80ccd_1b: Decimal = Decimal("0")     # NPS additional 50k (outside 80CCE)
    sec_80ccd_2: Decimal = Decimal("0")      # NPS employer contribution (no cap)
    sec_80d: Decimal = Decimal("0")          # health insurance premium
    sec_80dd: Decimal = Decimal("0")         # disabled dependent
    sec_80ddb: Decimal = Decimal("0")        # specified disease treatment
    sec_80e: Decimal = Decimal("0")          # education loan interest
    sec_80g: Decimal = Decimal("0")          # donations
    sec_80gg: Decimal = Decimal("0")         # rent paid (no HRA)
    sec_80tta: Decimal = Decimal("0")        # savings account interest (max 10k)
    sec_80ttb: Decimal = Decimal("0")        # senior citizen interest (max 50k)
    sec_80u: Decimal = Decimal("0")          # self disability
    total: Decimal = Decimal("0")


class Form16PartB(BaseModel):
    # Gross salary components (Sec 17)
    salary_17_1: Decimal = Decimal("0")      # salary, dearness allowance, etc.
    perquisites_17_2: Decimal = Decimal("0")
    profits_lieu_salary_17_3: Decimal = Decimal("0")
    gross_salary: Decimal = Decimal("0")

    # Exemptions u/s 10
    hra_received: Decimal = Decimal("0")     # HRA component in salary
    hra_exempt_10_13a: Decimal = Decimal("0")
    lta_exempt_10_5: Decimal = Decimal("0")
    other_exempt_10: Decimal = Decimal("0")
    total_exemptions: Decimal = Decimal("0")

    # Net salary after exemptions
    net_salary: Decimal = Decimal("0")

    # Deductions u/s 16
    standard_deduction_16: Decimal = Decimal("0")    # 50k / 75k from AY26
    entertainment_allowance_16_ii: Decimal = Decimal("0")
    professional_tax_16_iii: Decimal = Decimal("0")
    total_deductions_16: Decimal = Decimal("0")

    # Taxable salary
    income_from_salary: Decimal = Decimal("0")

    # Chapter VI-A
    deductions: Form16Deductions = Field(default_factory=Form16Deductions)

    # Final taxable income
    total_taxable_income: Decimal = Decimal("0")

    # Tax computation
    tax_on_total_income: Decimal = Decimal("0")
    rebate_87a: Decimal = Decimal("0")
    tax_after_rebate: Decimal = Decimal("0")
    surcharge: Decimal = Decimal("0")
    health_education_cess: Decimal = Decimal("0")    # 4% cess
    total_tax_payable: Decimal = Decimal("0")
    relief_89: Decimal = Decimal("0")
    net_tax_payable: Decimal = Decimal("0")

    # TDS summary
    tds_by_this_employer: Decimal = Decimal("0")
    tds_by_other_employers: Decimal = Decimal("0")
    total_tds: Decimal = Decimal("0")

    # Balance
    balance_tax_payable: Decimal = Decimal("0")      # negative = refund


class Form16Data(BaseModel):
    """Full parsed Form 16 — Part A + Part B."""
    part_a: Form16PartA = Field(default_factory=Form16PartA)
    part_b: Form16PartB = Field(default_factory=Form16PartB)
    parse_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    raw_text_length: int = 0
    warnings: list[str] = Field(default_factory=list)
    raw_extraction: dict[str, Any] = Field(default_factory=dict)


class Form16UploadResponse(BaseModel):
    status: str                              # "parsed" | "partial" | "failed"
    data: Form16Data
    message: str


# ── Regime comparison schemas ─────────────────────────────────────────────────

class SlabBreakdown(BaseModel):
    from_amount: Decimal
    to_amount: Decimal
    rate_pct: float
    tax: Decimal


class RegimeResult(BaseModel):
    """Full tax computation for one regime."""
    regime: str                              # "old" | "new"
    assessment_year: str                     # "2025-26" | "2026-27"

    # Income waterfall
    gross_salary: Decimal
    sec10_exemptions: Decimal                # HRA + LTA + other (old regime only)
    net_salary: Decimal
    standard_deduction: Decimal
    professional_tax: Decimal
    employer_nps_80ccd2: Decimal             # allowed in both regimes
    income_from_salary: Decimal
    additional_income: Decimal
    gross_total_income: Decimal
    chapter_via_deductions: Decimal          # old regime only
    total_taxable_income: Decimal

    # Tax computation
    tax_on_income: Decimal
    rebate_87a: Decimal
    tax_after_rebate: Decimal
    surcharge: Decimal
    cess: Decimal
    total_tax: Decimal

    # TDS & balance
    tds_deducted: Decimal
    balance_payable: Decimal                 # negative = refund due

    # Detail
    applicable_deductions: dict[str, Decimal]
    slab_breakdown: list[SlabBreakdown]


class RegimeComparison(BaseModel):
    old_regime: RegimeResult
    new_regime: RegimeResult
    recommended: str                         # "old" | "new"
    tax_difference: Decimal                  # new_tax − old_tax; negative = old costs less
    savings: Decimal                         # abs difference
    key_factors: list[str]
    financial_year: str
    assessment_year: str


class AdditionalIncome(BaseModel):
    interest_income: Decimal = Decimal("0")   # FD, savings interest
    rental_income: Decimal = Decimal("0")
    other_income: Decimal = Decimal("0")


class RegimeCompareRequest(BaseModel):
    form16: Form16Data
    additional_income: AdditionalIncome = Field(default_factory=AdditionalIncome)
    employer_nps_contribution: Decimal = Decimal("0")   # override if not clear from Form16
    age: int = Field(default=30, ge=18, le=100)
    assessment_year: str = Field(default="2025-26", pattern=r"^\d{4}-\d{2}$")


# ── P3: IT notice schemas ──────────────────────────────────────────────────────

class ITNoticeType(str, Enum):
    INTIMATION_143_1 = "143(1)"
    DEFECTIVE_139_9 = "139(9)"
    REASSESSMENT_148 = "148"
    REFUND_ADJUSTED_245 = "245"
    DEMAND_156 = "156"
    PENALTY_271 = "271"
    SUMMONS_131 = "131"
    UNKNOWN = "unknown"


class ITNotice(BaseModel):
    notice_type: ITNoticeType
    section: str | None = None
    assessment_year: str | None = None
    financial_year: str | None = None
    din: str | None = None              # Document Identification Number
    notice_date: str | None = None
    deadline: str | None = None         # response/compliance deadline
    amount_demanded: Decimal = Decimal("0")   # 0 = no demand; negative = refund
    compliance_required: str | None = None
    raw_text_length: int = 0
    parse_confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class NoticeExplanation(BaseModel):
    notice: ITNotice
    severity: str                       # "low" | "medium" | "high" | "critical"
    plain_english: str
    action_required: str
    deadline_urgent: bool               # deadline within 30 days
    key_points: list[str]
    do_not_ignore: bool


# ── P4: Capital gains schemas ──────────────────────────────────────────────────

class CapitalGainsCategory(str, Enum):
    EQUITY_STCG = "equity_stcg"        # listed equity/equity MF ≤12m
    EQUITY_LTCG = "equity_ltcg"        # listed equity/equity MF >12m
    DEBT_STCG = "debt_stcg"            # debt instruments ≤36m, slab rate
    DEBT_LTCG = "debt_ltcg"            # debt instruments >36m, slab rate
    OTHER_STCG = "other_stcg"
    OTHER_LTCG = "other_ltcg"


class CapitalGainsTrade(BaseModel):
    symbol: str
    isin: str | None = None
    quantity: Decimal
    buy_date: str
    sell_date: str
    buy_amount: Decimal
    sell_amount: Decimal
    gain_loss: Decimal
    holding_days: int
    category: CapitalGainsCategory
    tax_rate_pct: float | None = None   # None = slab-rated


class CapitalGainsSummary(BaseModel):
    trades: list[CapitalGainsTrade]

    # Equity gains split by Budget 2024 date (Jul 23, 2024)
    # Pre-budget: STCG 15%, LTCG 10% with ₹1L exemption
    # Post-budget: STCG 20%, LTCG 12.5% with ₹1.25L exemption
    pre_budget_eq_stcg: Decimal = Decimal("0")
    post_budget_eq_stcg: Decimal = Decimal("0")
    pre_budget_eq_ltcg: Decimal = Decimal("0")
    post_budget_eq_ltcg: Decimal = Decimal("0")

    # Convenience totals
    equity_stcg: Decimal = Decimal("0")
    equity_ltcg: Decimal = Decimal("0")
    equity_ltcg_taxable: Decimal = Decimal("0")  # after exemption
    debt_stcg: Decimal = Decimal("0")
    debt_ltcg: Decimal = Decimal("0")
    other_stcg: Decimal = Decimal("0")
    other_ltcg: Decimal = Decimal("0")
    total_gains: Decimal = Decimal("0")
    total_losses: Decimal = Decimal("0")

    # Tax (equity only; debt/other taxed at slab rate — add to income)
    tax_equity_stcg: Decimal = Decimal("0")
    tax_equity_ltcg: Decimal = Decimal("0")
    total_capital_gains_tax: Decimal = Decimal("0")

    broker: str                         # "zerodha" | "groww" | "generic"
    total_trades: int
    financial_year: str
    assessment_year: str
    warnings: list[str] = Field(default_factory=list)


class CapitalGainsUploadResponse(BaseModel):
    status: str                         # "parsed" | "partial"
    data: CapitalGainsSummary
    message: str


# ── P2-B: AIS schemas ─────────────────────────────────────────────────────────

class AISIncomeItem(BaseModel):
    category: str                       # salary_tds | interest_tds | interest_credited
                                        # dividend | securities_sale | mf_sale
                                        # advance_tax | self_assessment_tax
    description: str
    payer_name: str | None = None
    payer_tan_pan: str | None = None
    amount: Decimal = Decimal("0")      # gross income amount
    tds_deducted: Decimal = Decimal("0")


class AISData(BaseModel):
    pan: str | None = None
    taxpayer_name: str | None = None
    assessment_year: str | None = None
    income_items: list[AISIncomeItem] = Field(default_factory=list)
    total_tds_from_salary: Decimal = Decimal("0")
    total_tds_from_others: Decimal = Decimal("0")
    total_interest_income: Decimal = Decimal("0")
    total_dividend_income: Decimal = Decimal("0")
    total_securities_sale_value: Decimal = Decimal("0")
    total_mf_redemption_value: Decimal = Decimal("0")
    advance_tax_paid: Decimal = Decimal("0")
    self_assessment_tax_paid: Decimal = Decimal("0")
    parse_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    raw_text_length: int = 0
    warnings: list[str] = Field(default_factory=list)


class AISUploadResponse(BaseModel):
    status: str
    data: AISData
    message: str


class ReconciliationItem(BaseModel):
    category: str                       # tds_salary | interest | dividend | capital_gains
    description: str
    form16_amount: Decimal | None = None
    ais_amount: Decimal | None = None
    declared_amount: Decimal | None = None
    delta: Decimal = Decimal("0")       # ais − declared; negative = over-declared
    severity: str                       # "info" | "warning" | "error"
    action: str


class ReconciliationReport(BaseModel):
    items: list[ReconciliationItem]
    filing_risk: str                    # "low" | "medium" | "high"
    undeclared_income: Decimal          # income in AIS not declared by user
    total_discrepancies: int
    ok_count: int
    recommendations: list[str]
    assessment_year: str


class ReconcileRequest(BaseModel):
    form16: Form16Data
    ais: AISData
    capital_gains: CapitalGainsSummary | None = None
    additional_income: AdditionalIncome = Field(default_factory=AdditionalIncome)


# ── P2-A: ITR XML schemas ─────────────────────────────────────────────────────

class PersonalInfo(BaseModel):
    first_name: str
    middle_name: str = ""
    last_name: str
    pan: str
    aadhaar: str = ""                   # 12-digit, optional
    dob: str                            # DD/MM/YYYY
    father_name: str = ""
    mobile: str = ""
    email: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state_code: str = "27"              # 2-digit IT dept state code; 27=Maharashtra
    pin_code: str = ""
    employer_category: str = "OTH"     # GOV | PSU | OTH | PEN


class ITRXMLRequest(BaseModel):
    personal_info: PersonalInfo
    form16: Form16Data
    regime: str = Field(default="new", pattern=r"^(old|new)$")
    assessment_year: str = Field(default="2025-26", pattern=r"^\d{4}-\d{2}$")
    additional_income: AdditionalIncome = Field(default_factory=AdditionalIncome)
    capital_gains: CapitalGainsSummary | None = None
    house_property_income: Decimal = Decimal("0")   # annual rent − 30% std deduction


class ITRXMLResponse(BaseModel):
    itr_form: str                       # "ITR-1" | "ITR-2"
    xml_content: str
    assessment_year: str
    taxable_income: Decimal
    total_tax: Decimal
    tds_deducted: Decimal
    balance_payable: Decimal            # negative = refund
    warnings: list[str]
    notes: list[str]
