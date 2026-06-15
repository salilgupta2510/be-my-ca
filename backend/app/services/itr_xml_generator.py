"""
ITR XML Generator — ITR-1 (Sahaj) / ITR-2.

Uses IT department's published schema structure to generate spec-compliant XML
that taxpayers upload directly at incometax.gov.in (e-File → Income Tax Returns
→ File Income Tax Return → Upload XML).

ITR-1 (Sahaj) eligibility:
  - Salary income only (or one house property)
  - No capital gains
  - Total income ≤ ₹50L

ITR-2 required when:
  - Capital gains of any kind
  - Multiple house properties
  - Foreign assets / foreign income

ERI registration NOT required — users upload XML themselves via IT portal.

XML structure follows ITR-1 / ITR-2 schema (AY 2025-26).
Reference: incometax.gov.in/iec/foportal/help/e-filing-user-manual
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.itr import (
    AdditionalIncome,
    CapitalGainsSummary,
    Form16Data,
    ITRXMLRequest,
    ITRXMLResponse,
    PersonalInfo,
)

# ── Tax computation helpers ────────────────────────────────────────────────────

_CESS_RATE = Decimal("0.04")

_NEW_REGIME_SLABS_2526 = [
    # (from, to_exclusive, rate)
    (Decimal("0"), Decimal("400000"), Decimal("0")),
    (Decimal("400000"), Decimal("800000"), Decimal("0.05")),
    (Decimal("800000"), Decimal("1200000"), Decimal("0.10")),
    (Decimal("1200000"), Decimal("1600000"), Decimal("0.15")),
    (Decimal("1600000"), Decimal("2000000"), Decimal("0.20")),
    (Decimal("2000000"), Decimal("2400000"), Decimal("0.25")),
    (Decimal("2400000"), Decimal("9999999999"), Decimal("0.30")),
]

_OLD_REGIME_SLABS_2526 = [
    (Decimal("0"), Decimal("250000"), Decimal("0")),
    (Decimal("250000"), Decimal("500000"), Decimal("0.05")),
    (Decimal("500000"), Decimal("1000000"), Decimal("0.20")),
    (Decimal("1000000"), Decimal("9999999999"), Decimal("0.30")),
]


def _slab_tax(income: Decimal, slabs: list) -> Decimal:
    tax = Decimal("0")
    for lo, hi, rate in slabs:
        if income <= lo:
            break
        taxable = min(income, hi) - lo
        tax += taxable * rate
    return tax.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _rebate_87a(tax: Decimal, income: Decimal, regime: str) -> Decimal:
    """Sec 87A rebate: full tax rebate if income ≤ ₹7L (new) or ₹5L (old), capped at ₹25k."""
    limit = Decimal("700000") if regime == "new" else Decimal("500000")
    if income <= limit:
        return min(tax, Decimal("25000"))
    return Decimal("0")


def _surcharge(tax: Decimal, income: Decimal) -> Decimal:
    if income <= Decimal("5000000"):
        return Decimal("0")
    if income <= Decimal("10000000"):
        return (tax * Decimal("0.10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if income <= Decimal("20000000"):
        return (tax * Decimal("0.15")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if income <= Decimal("50000000"):
        return (tax * Decimal("0.25")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (tax * Decimal("0.37")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _i(v: Decimal | None) -> str:
    """Decimal → integer string for XML (IT dept uses integer rupees)."""
    if v is None:
        return "0"
    return str(int(v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def _determine_itr_form(
    capital_gains: CapitalGainsSummary | None,
    house_property_income: Decimal,
    total_income: Decimal,
) -> str:
    if capital_gains is not None and capital_gains.total_trades > 0:
        return "ITR-2"
    if house_property_income != 0:
        return "ITR-2"
    if total_income > Decimal("5000000"):
        return "ITR-2"
    return "ITR-1"


# ── Income waterfall ───────────────────────────────────────────────────────────

def _compute_income(
    form16: Form16Data,
    additional_income: AdditionalIncome,
    capital_gains: CapitalGainsSummary | None,
    house_property_income: Decimal,
    regime: str,
    ay: str,
) -> dict:
    pb = form16.part_b
    pa = form16.part_a

    gross_salary = pb.gross_salary or pa.total_tds_deducted * Decimal("10")  # rough fallback

    # Section 10 exemptions — only in old regime
    if regime == "old":
        sec10_exempt = pb.total_exemptions
    else:
        sec10_exempt = Decimal("0")  # HRA/LTA not allowed in new regime

    net_salary = gross_salary - sec10_exempt

    # Standard deduction u/s 16(ia): ₹75,000 for AY 2026-27, ₹50,000 for AY 2025-26
    std_ded = Decimal("75000") if ay == "2026-27" else Decimal("50000")
    prof_tax = pb.professional_tax_16_iii

    income_from_salary = max(Decimal("0"), net_salary - std_ded - prof_tax)

    # Additional income
    interest = additional_income.interest_income
    rental = additional_income.rental_income
    other = additional_income.other_income

    gross_total = income_from_salary + house_property_income + interest + rental + other

    # Chapter VI-A deductions — only old regime
    if regime == "old":
        d = pb.deductions
        ch6a = min(d.total or (
            d.sec_80c + d.sec_80ccc + d.sec_80ccd_1 + d.sec_80ccd_1b
            + d.sec_80ccd_2 + d.sec_80d + d.sec_80dd + d.sec_80ddb
            + d.sec_80e + d.sec_80g + d.sec_80gg + d.sec_80tta + d.sec_80ttb + d.sec_80u
        ), Decimal("999999999"))
    else:
        ch6a = pb.deductions.sec_80ccd_2  # only employer NPS allowed in new regime

    taxable_income = max(Decimal("0"), gross_total - ch6a)

    # Capital gains tax (computed at special rates, not via slabs)
    cg_tax = Decimal("0")
    if capital_gains:
        cg_tax = capital_gains.total_capital_gains_tax
        # Debt CG + debt income add to slab income
        taxable_income += capital_gains.debt_stcg + capital_gains.debt_ltcg

    # Slab tax on non-capital-gains income
    slabs = _NEW_REGIME_SLABS_2526 if regime == "new" else _OLD_REGIME_SLABS_2526
    slab_tax = _slab_tax(taxable_income, slabs)

    total_pre_rebate = slab_tax + cg_tax

    # 87A rebate applies only to slab tax, not to special-rate CG tax
    rebate = _rebate_87a(slab_tax, taxable_income, regime)
    tax_after_rebate = max(Decimal("0"), slab_tax - rebate) + cg_tax

    surcharge = _surcharge(tax_after_rebate, taxable_income)
    tax_plus_surcharge = tax_after_rebate + surcharge
    cess = (tax_plus_surcharge * _CESS_RATE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    total_tax = tax_plus_surcharge + cess

    tds = pa.total_tds_deducted
    balance = total_tax - tds

    return {
        "gross_salary": gross_salary,
        "sec10_exempt": sec10_exempt,
        "net_salary": net_salary,
        "std_ded": std_ded,
        "prof_tax": prof_tax,
        "income_from_salary": income_from_salary,
        "interest": interest,
        "rental": rental,
        "other": other,
        "house_property_income": house_property_income,
        "gross_total": gross_total,
        "ch6a": ch6a,
        "taxable_income": taxable_income,
        "slab_tax": slab_tax,
        "cg_tax": cg_tax,
        "rebate": rebate,
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total_tax,
        "tds": tds,
        "balance": balance,
    }


# ── ITR-1 XML builder ──────────────────────────────────────────────────────────

def _build_itr1_xml(
    req: ITRXMLRequest,
    inc: dict,
    warnings: list[str],
) -> str:
    pi = req.personal_info
    pb = req.form16.part_b
    pa = req.form16.part_a
    ay = req.assessment_year
    # ay "2025-26" → fy "2024-25"
    try:
        ay_start = int(ay[:4])
        fy = f"{ay_start - 1}-{str(ay_start)[-2:]}"
    except (ValueError, IndexError):
        fy = "2024-25"

    root = ET.Element("ITR", attrib={
        "xmlns": "http://incometaxindiaefiling.gov.in/master",
        "Form_Name": "ITR-1",
        "Description": "For Individuals having Income from Salary/One House Property/Other Sources",
        "Assessment_Year": ay,
        "FY": fy,
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    })

    itr1 = ET.SubElement(root, "ITR1")

    # ── Personal Info ──────────────────────────────────────────────────────────
    pinfo = ET.SubElement(itr1, "PersonalInfo")
    _t(pinfo, "AssesseeName", " ".join(filter(None, [pi.first_name, pi.middle_name, pi.last_name])))
    _t(pinfo, "PAN", pi.pan.upper())
    _t(pinfo, "DOB", pi.dob)
    _t(pinfo, "AadhaarCardNo", pi.aadhaar or "")
    _t(pinfo, "FatherName", pi.father_name)
    _t(pinfo, "Address", pi.address_line1)
    _t(pinfo, "CityOrTownOrDistrict", pi.city)
    _t(pinfo, "StateCode", pi.state_code)
    _t(pinfo, "PinCode", pi.pin_code)
    _t(pinfo, "CountryCode", "91")
    _t(pinfo, "MobileNo", pi.mobile)
    _t(pinfo, "EmailAddress", pi.email)
    _t(pinfo, "EmployerCategory", pi.employer_category)
    _t(pinfo, "ResidentialStatus", "RES")  # resident; non-residents need ITR-2
    _t(pinfo, "TaxStatus", "11")  # individual

    # ── Filing Info ────────────────────────────────────────────────────────────
    fi = ET.SubElement(itr1, "FilingStatus")
    _t(fi, "ReturnFileSec", "11")   # 11 = 139(1) original return before due date
    _t(fi, "NewTaxRegime", "Y" if req.regime == "new" else "N")
    _t(fi, "OptNewRegime", "Y" if req.regime == "new" else "N")
    _t(fi, "SeventhProvisio139", "N")

    # ── Income Details ─────────────────────────────────────────────────────────
    id_el = ET.SubElement(itr1, "ITR1_IncomeDeductions")
    _t(id_el, "GrossSalary", _i(inc["gross_salary"]))
    _t(id_el, "Salary17_1", _i(pb.salary_17_1 or inc["gross_salary"]))
    _t(id_el, "PerquisitesValue", _i(pb.perquisites_17_2))
    _t(id_el, "ProfitsinLieuOfSalary", _i(pb.profits_lieu_salary_17_3))
    _t(id_el, "AllwncExemptUs10", _i(inc["sec10_exempt"]))
    _t(id_el, "NetSalary", _i(inc["net_salary"]))
    _t(id_el, "DeductionUs16", _i(inc["std_ded"] + inc["prof_tax"]))
    _t(id_el, "StandardDeduction", _i(inc["std_ded"]))
    _t(id_el, "ProfTax", _i(inc["prof_tax"]))
    _t(id_el, "IncomeFromSal", _i(inc["income_from_salary"]))

    _t(id_el, "IncomeOthSrc", _i(inc["interest"] + inc["other"]))
    _t(id_el, "IntrstFrmSavAcc", _i(Decimal("0")))  # savings acc interest (80TTA)
    _t(id_el, "IntrstFrmDpt", _i(inc["interest"]))
    _t(id_el, "DividendGrossAmt", _i(Decimal("0")))

    _t(id_el, "GrossTotIncome", _i(inc["gross_total"]))

    # Deductions
    ded = ET.SubElement(id_el, "DeductionUnderChap6A")
    d = pb.deductions
    _t(ded, "Section80C", _i(d.sec_80c))
    _t(ded, "Section80CCC", _i(d.sec_80ccc))
    _t(ded, "Section80CCDEmployeeOrSE", _i(d.sec_80ccd_1))
    _t(ded, "Section80CCD1B", _i(d.sec_80ccd_1b))
    _t(ded, "Section80CCDEmployer", _i(d.sec_80ccd_2))
    _t(ded, "Section80D", _i(d.sec_80d))
    _t(ded, "Section80E", _i(d.sec_80e))
    _t(ded, "Section80G", _i(d.sec_80g))
    _t(ded, "Section80GG", _i(d.sec_80gg))
    _t(ded, "Section80TTA", _i(d.sec_80tta))
    _t(ded, "Section80TTB", _i(d.sec_80ttb))
    _t(ded, "Section80U", _i(d.sec_80u))
    _t(ded, "TotalChapVIADeductions", _i(inc["ch6a"]))

    _t(id_el, "TotalIncome", _i(inc["taxable_income"]))

    # ── Tax Computation ────────────────────────────────────────────────────────
    tc = ET.SubElement(itr1, "ITR1_TaxComputation")
    _t(tc, "TotalTaxPayable", _i(inc["slab_tax"]))
    _t(tc, "Rebate87A", _i(inc["rebate"]))
    _t(tc, "TaxPayableAfterRebate", _i(max(Decimal("0"), inc["slab_tax"] - inc["rebate"])))
    _t(tc, "Surcharge", _i(inc["surcharge"]))
    _t(tc, "EducationCess", _i(inc["cess"]))
    _t(tc, "GrossTaxLiability", _i(inc["total_tax"]))
    _t(tc, "NetTaxLiability", _i(inc["total_tax"]))
    _t(tc, "TotalIntrstPay", "0")
    _t(tc, "IntrstPayUs234A", "0")
    _t(tc, "IntrstPayUs234B", "0")
    _t(tc, "IntrstPayUs234C", "0")
    _t(tc, "TotTaxPlusIntrstPay", _i(inc["total_tax"]))

    # ── TDS ────────────────────────────────────────────────────────────────────
    tds_el = ET.SubElement(itr1, "TDSonSalaries")
    tds_row = ET.SubElement(tds_el, "TDSonSalary")
    _t(tds_row, "EmployerOrDeductorOrCollectTAN", pa.employer_tan or "NOTAVAILABLE")
    _t(tds_row, "EmployerOrDeductorOrCollectName", pa.employer_name or "")
    _t(tds_row, "IncChrgSal", _i(inc["income_from_salary"]))
    _t(tds_row, "TotalTDSSal", _i(inc["tds"]))

    # ── Tax Paid ───────────────────────────────────────────────────────────────
    tp = ET.SubElement(itr1, "TaxPaid")
    _t(tp, "TotalTDSSal", _i(inc["tds"]))
    _t(tp, "TotalTDSOthThanSal", "0")
    _t(tp, "TotalTCS", "0")
    _t(tp, "TotalAdvTax", "0")
    _t(tp, "TotalSelfAssTax", "0")
    _t(tp, "TotalTaxesPaid", _i(inc["tds"]))
    _t(tp, "BalTaxPayable", _i(max(Decimal("0"), inc["balance"])))
    _t(tp, "Refund", _i(max(Decimal("0"), -inc["balance"])))

    # ── Verification ──────────────────────────────────────────────────────────
    veri = ET.SubElement(itr1, "Verification")
    _t(veri, "Declaration", (
        "I, solemnly declare that to the best of my knowledge and belief, "
        "the information given in the return is correct and complete."
    ))
    _t(veri, "Capacity", "S")  # S = Self
    _t(veri, "Place", pi.city or "")
    _t(veri, "Date", "")  # user fills at upload

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ── ITR-2 XML builder ──────────────────────────────────────────────────────────

def _build_itr2_xml(
    req: ITRXMLRequest,
    inc: dict,
    warnings: list[str],
) -> str:
    pi = req.personal_info
    pb = req.form16.part_b
    pa = req.form16.part_a
    cg = req.capital_gains
    ay = req.assessment_year
    try:
        ay_start = int(ay[:4])
        fy = f"{ay_start - 1}-{str(ay_start)[-2:]}"
    except (ValueError, IndexError):
        fy = "2024-25"

    root = ET.Element("ITR", attrib={
        "xmlns": "http://incometaxindiaefiling.gov.in/master",
        "Form_Name": "ITR-2",
        "Description": "For Individuals and HUFs not having income from profits and gains of business or profession",
        "Assessment_Year": ay,
        "FY": fy,
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    })

    itr2 = ET.SubElement(root, "ITR2")

    # ── Part A General ─────────────────────────────────────────────────────────
    pag = ET.SubElement(itr2, "PartA_GEN1")
    personal = ET.SubElement(pag, "PersonalInfo")
    _t(personal, "AssesseeName", f"{pi.first_name} {pi.middle_name} {pi.last_name}".strip())
    _t(personal, "PAN", pi.pan.upper())
    _t(personal, "DOB", pi.dob)
    _t(personal, "AadhaarCardNo", pi.aadhaar or "")
    _t(personal, "FatherName", pi.father_name)
    addr = ET.SubElement(personal, "Address")
    _t(addr, "ResidenceNo", pi.address_line1)
    _t(addr, "LocalityOrArea", pi.address_line2)
    _t(addr, "CityOrTownOrDistrict", pi.city)
    _t(addr, "StateCode", pi.state_code)
    _t(addr, "PinCode", pi.pin_code)
    _t(addr, "CountryCode", "91")
    _t(personal, "MobileNo", pi.mobile)
    _t(personal, "EmailAddress", pi.email)
    _t(personal, "EmployerCategory", pi.employer_category)
    _t(personal, "ResidentialStatus", "RES")

    fs = ET.SubElement(pag, "FilingStatus")
    _t(fs, "ReturnFileSec", "11")
    _t(fs, "NewTaxRegime", "Y" if req.regime == "new" else "N")

    # ── Schedule S (Salary) ────────────────────────────────────────────────────
    sch_s = ET.SubElement(itr2, "ScheduleS")
    _t(sch_s, "GrossSalary", _i(inc["gross_salary"]))
    _t(sch_s, "AllwncExemptUs10", _i(inc["sec10_exempt"]))
    _t(sch_s, "NetSalary", _i(inc["net_salary"]))
    _t(sch_s, "DeductionUs16", _i(inc["std_ded"] + inc["prof_tax"]))
    _t(sch_s, "IncomeFromSal", _i(inc["income_from_salary"]))

    # ── Schedule HP (House Property) ──────────────────────────────────────────
    if inc["house_property_income"] != 0:
        sch_hp = ET.SubElement(itr2, "ScheduleHP")
        hp_entry = ET.SubElement(sch_hp, "PassThroghIncome")
        _t(hp_entry, "IncomeFromHP", _i(inc["house_property_income"]))

    # ── Schedule CG (Capital Gains) ───────────────────────────────────────────
    if cg and cg.total_trades > 0:
        sch_cg = ET.SubElement(itr2, "ScheduleCG")

        # Short-term capital gains
        stcg = ET.SubElement(sch_cg, "ShortTermCapGainFor23")
        _t(stcg, "EquityMFonSTT", _i(cg.equity_stcg))
        _t(stcg, "TotalSTCG", _i(cg.equity_stcg + cg.debt_stcg + cg.other_stcg))

        # Long-term capital gains
        ltcg = ET.SubElement(sch_cg, "LongTermCapGain23")
        _t(ltcg, "SaleValueOfEquityMF", _i(cg.equity_ltcg + cg.equity_ltcg_taxable))
        _t(ltcg, "LTCGbeforeLoss", _i(cg.equity_ltcg))
        _t(ltcg, "Exemption112A", _i(cg.equity_ltcg - cg.equity_ltcg_taxable))
        _t(ltcg, "TotalLTCG", _i(cg.equity_ltcg_taxable + cg.debt_ltcg + cg.other_ltcg))

        # Pre/post budget 2024 split for FY 2024-25
        if cg.pre_budget_eq_stcg != 0 or cg.post_budget_eq_stcg != 0:
            bsplit = ET.SubElement(sch_cg, "Budget2024CGSplit")
            _t(bsplit, "PreBudgetSTCG15Pct", _i(cg.pre_budget_eq_stcg))
            _t(bsplit, "PostBudgetSTCG20Pct", _i(cg.post_budget_eq_stcg))
            _t(bsplit, "PreBudgetLTCG10Pct", _i(cg.pre_budget_eq_ltcg))
            _t(bsplit, "PostBudgetLTCG12_5Pct", _i(cg.post_budget_eq_ltcg))

        _t(sch_cg, "TotalCapGains", _i(
            cg.equity_stcg + cg.equity_ltcg_taxable
            + cg.debt_stcg + cg.debt_ltcg
            + cg.other_stcg + cg.other_ltcg
        ))

    # ── Schedule OS (Other Sources) ────────────────────────────────────────────
    sch_os = ET.SubElement(itr2, "ScheduleOS")
    _t(sch_os, "IntrstFrmDpt", _i(inc["interest"]))
    _t(sch_os, "OthersInc", _i(inc["other"]))
    _t(sch_os, "IncFrmOS", _i(inc["interest"] + inc["other"]))

    # ── Part B TTI (Total Tax and Income) ─────────────────────────────────────
    tti = ET.SubElement(itr2, "PartB_TTI")
    _t(tti, "TotalIncome", _i(inc["taxable_income"]))
    _t(tti, "GrossTaxLiability", _i(inc["total_tax"]))
    _t(tti, "Rebate87A", _i(inc["rebate"]))
    _t(tti, "Surcharge", _i(inc["surcharge"]))
    _t(tti, "EducationCess", _i(inc["cess"]))
    _t(tti, "NetTaxLiability", _i(inc["total_tax"]))
    _t(tti, "TotalTaxesPaid", _i(inc["tds"]))
    _t(tti, "BalTaxPayable", _i(max(Decimal("0"), inc["balance"])))
    _t(tti, "Refund", _i(max(Decimal("0"), -inc["balance"])))

    # TDS schedule
    sch_tds1 = ET.SubElement(itr2, "ScheduleTDS1")
    tds_row = ET.SubElement(sch_tds1, "TDSonSalaries")
    _t(tds_row, "EmployerOrDeductorTAN", pa.employer_tan or "NOTAVAILABLE")
    _t(tds_row, "EmployerOrDeductorName", pa.employer_name or "")
    _t(tds_row, "IncOfEmployee", _i(inc["income_from_salary"]))
    _t(tds_row, "TaxDeducted", _i(inc["tds"]))

    # Verification
    veri = ET.SubElement(itr2, "Verification")
    _t(veri, "Declaration", (
        "I, solemnly declare that to the best of my knowledge and belief, "
        "the information given in the return is correct and complete."
    ))
    _t(veri, "Capacity", "S")
    _t(veri, "Place", pi.city or "")
    _t(veri, "Date", "")

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _t(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_itr_xml(req: ITRXMLRequest) -> ITRXMLResponse:
    warnings: list[str] = []
    notes: list[str] = []

    pb = req.form16.part_b
    if pb.gross_salary == 0 and req.form16.part_a.total_tds_deducted == 0:
        warnings.append("No salary data found in Form 16. XML will have zero income — verify before upload.")

    if req.form16.parse_confidence < 0.5:
        warnings.append(f"Form 16 parse confidence is low ({req.form16.parse_confidence:.0%}). Verify all figures.")

    inc = _compute_income(
        form16=req.form16,
        additional_income=req.additional_income,
        capital_gains=req.capital_gains,
        house_property_income=req.house_property_income,
        regime=req.regime,
        ay=req.assessment_year,
    )

    itr_form = _determine_itr_form(
        req.capital_gains, req.house_property_income, inc["taxable_income"]
    )

    if itr_form == "ITR-2":
        xml_content = _build_itr2_xml(req, inc, warnings)
    else:
        xml_content = _build_itr1_xml(req, inc, warnings)

    if req.regime == "new" and pb.deductions.sec_80c > 0:
        notes.append(
            "New regime selected but Form 16 has 80C deductions. "
            "These are not applicable in new regime. Switch to old regime if deductions are significant."
        )

    if inc["balance"] < 0:
        notes.append(f"Refund of ₹{abs(inc['balance']):,.0f} due. Will be credited to bank account linked with PAN.")
    elif inc["balance"] > 0:
        notes.append(
            f"Tax of ₹{inc['balance']:,.0f} payable. Pay via Challan 280 (IT portal → e-Pay Tax) "
            "before uploading this XML."
        )

    notes.append(
        f"Upload {itr_form} XML at incometax.gov.in → e-File → Income Tax Returns → "
        "File Income Tax Return → Online → Upload XML."
    )

    return ITRXMLResponse(
        itr_form=itr_form,
        xml_content=xml_content,
        assessment_year=req.assessment_year,
        taxable_income=inc["taxable_income"],
        total_tax=inc["total_tax"],
        tds_deducted=inc["tds"],
        balance_payable=inc["balance"],
        warnings=warnings,
        notes=notes,
    )
