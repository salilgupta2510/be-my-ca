"""
ITR endpoints.

  POST /itr/form16/upload         — parse Form 16 PDF, return structured data
  POST /itr/regime-compare        — compare old vs new tax regime, recommend better
  POST /itr/notice/upload         — parse IT dept notice PDF, explain in plain English
  POST /itr/capital-gains/upload  — parse broker P&L CSV, compute capital gains tax
  POST /itr/ais/upload            — parse Annual Information Statement (JSON or PDF)
  POST /itr/reconcile             — diff AIS vs Form 16 vs CG CSV, flag discrepancies
  POST /itr/generate-xml          — generate ITR-1/ITR-2 XML for manual portal upload
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.itr import (
    AISUploadResponse,
    CapitalGainsUploadResponse,
    Form16UploadResponse,
    ITRXMLRequest,
    ITRXMLResponse,
    NoticeExplanation,
    ReconcileRequest,
    ReconciliationReport,
    RegimeCompareRequest,
    RegimeComparison,
)
from app.services.ais_parser import parse_ais
from app.services.capital_gains import parse_capital_gains_csv
from app.services.form16_parser import parse_form16
from app.services.itr_engine import compare_regimes
from app.services.itr_xml_generator import generate_itr_xml
from app.services.notice_handler import parse_notice
from app.services.reconciler import reconcile

router = APIRouter(prefix="/itr", tags=["ITR"])

_MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


@router.post("/form16/upload", response_model=Form16UploadResponse)
async def upload_form16(
    file: UploadFile = File(..., description="Form 16 PDF (Part A + Part B)"),
    current_user: User = Depends(get_current_user),
) -> Form16UploadResponse:
    """
    Parse an employer-issued Form 16 PDF.

    Returns structured salary, exemption, deduction, and TDS data
    extracted from Part A and Part B.
    """
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_CONTENT_TYPES and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files accepted.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(413, "File too large. Maximum 10 MB.")
    if len(pdf_bytes) < 100:
        raise HTTPException(400, "File appears empty or corrupt.")

    try:
        data = await parse_form16(pdf_bytes, filename=file.filename or "form16.pdf")
    except ValueError as e:
        raise HTTPException(422, str(e))

    if data.parse_confidence < 0.3:
        status = "partial"
        message = "Low confidence parse. Verify figures manually before use."
    elif data.warnings:
        status = "partial"
        message = f"Parsed with {len(data.warnings)} warning(s). Review before filing."
    else:
        status = "parsed"
        message = "Form 16 parsed successfully."

    return Form16UploadResponse(status=status, data=data, message=message)


@router.post("/regime-compare", response_model=RegimeComparison)
def regime_compare(
    body: RegimeCompareRequest,
    current_user: User = Depends(get_current_user),
) -> RegimeComparison:
    """
    Compare old vs new tax regime using Form 16 data.

    Pass the Form16Data from /itr/form16/upload plus any additional
    income (interest, rental) and personal details (age, AY).

    Returns full waterfall for both regimes, recommendation, and
    plain-language key factors.
    """
    supported_ay = {"2025-26", "2026-27"}
    if body.assessment_year not in supported_ay:
        raise HTTPException(400, f"Supported assessment years: {sorted(supported_ay)}")

    ai = body.additional_income
    return compare_regimes(
        form16=body.form16,
        additional_interest=ai.interest_income,
        additional_rental=ai.rental_income,
        additional_other=ai.other_income,
        employer_nps=body.employer_nps_contribution,
        age=body.age,
        ay=body.assessment_year,
    )


_MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/notice/upload", response_model=NoticeExplanation)
async def upload_notice(
    file: UploadFile = File(..., description="Income Tax department notice PDF"),
    current_user: User = Depends(get_current_user),
) -> NoticeExplanation:
    """
    Parse an Income Tax department notice PDF.

    Returns severity, plain-language explanation, deadline urgency,
    and step-by-step action required.
    """
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_CONTENT_TYPES and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files accepted.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(413, "File too large. Maximum 10 MB.")
    if len(pdf_bytes) < 100:
        raise HTTPException(400, "File appears empty or corrupt.")

    try:
        result = await parse_notice(pdf_bytes, filename=file.filename or "notice.pdf")
    except ValueError as e:
        raise HTTPException(422, str(e))

    return result


@router.post("/capital-gains/upload", response_model=CapitalGainsUploadResponse)
async def upload_capital_gains(
    file: UploadFile = File(..., description="Broker P&L CSV (Zerodha Tax P&L or Groww Realized P&L)"),
    current_user: User = Depends(get_current_user),
) -> CapitalGainsUploadResponse:
    """
    Parse a broker P&L CSV and compute capital gains tax.

    Supports Zerodha Tax P&L (Console → Reports → Tax P&L) and
    Groww Realized P&L exports. Applies Budget 2024 rate split for FY 2024-25.

    Equity STCG: 20% (15% pre-Jul 23 2024).
    Equity LTCG: 12.5% above ₹1.25L (10% pre-Jul 23 2024 above ₹1L).
    Debt: slab-rated — add to income via /itr/regime-compare.
    """
    filename = file.filename or "trades.csv"
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if (
        not filename.lower().endswith(".csv")
        and "csv" not in content_type
        and "text" not in content_type
        and "spreadsheet" not in content_type
    ):
        raise HTTPException(415, "Only CSV files accepted.")

    csv_bytes = await file.read()
    if len(csv_bytes) > _MAX_CSV_BYTES:
        raise HTTPException(413, "File too large. Maximum 5 MB.")
    if len(csv_bytes) < 10:
        raise HTTPException(400, "File appears empty.")

    try:
        data = parse_capital_gains_csv(csv_bytes, filename=filename)
    except ValueError as e:
        raise HTTPException(422, str(e))

    has_warnings = bool(data.warnings)
    status = "partial" if has_warnings else "parsed"
    message = f"Parsed {data.total_trades} trades from {data.broker} export."
    if has_warnings:
        message += f" {len(data.warnings)} warning(s) — review before filing."

    return CapitalGainsUploadResponse(status=status, data=data, message=message)


_MAX_AIS_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/ais/upload", response_model=AISUploadResponse)
async def upload_ais(
    file: UploadFile = File(..., description="Annual Information Statement — JSON or PDF from IT portal"),
    current_user: User = Depends(get_current_user),
) -> AISUploadResponse:
    """
    Parse Annual Information Statement (AIS).

    Download from IT portal: e-Filing → AIS/TIS → Download.
    JSON format preferred (more reliable extraction than PDF).

    Returns all income items, TDS totals, and securities/MF sale values
    to be used in reconcile and generate-xml flows.
    """
    filename = file.filename or "ais.json"
    fname_lower = filename.lower()
    content_type = (file.content_type or "").lower().split(";")[0].strip()

    allowed_pdf = content_type in {"application/pdf", "application/x-pdf"} or fname_lower.endswith(".pdf")
    allowed_json = "json" in content_type or fname_lower.endswith(".json")
    if not (allowed_pdf or allowed_json):
        raise HTTPException(415, "Only AIS JSON or AIS PDF accepted.")

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_AIS_BYTES:
        raise HTTPException(413, "File too large. Maximum 10 MB.")
    if len(file_bytes) < 10:
        raise HTTPException(400, "File appears empty.")

    try:
        data = await parse_ais(file_bytes, filename=filename)
    except ValueError as e:
        raise HTTPException(422, str(e))

    has_warnings = bool(data.warnings)
    status = "partial" if has_warnings else "parsed"
    item_count = len(data.income_items)
    message = f"AIS parsed — {item_count} income item(s) found."
    if has_warnings:
        message += f" {len(data.warnings)} warning(s)."

    return AISUploadResponse(status=status, data=data, message=message)


@router.post("/reconcile", response_model=ReconciliationReport)
def reconcile_income(
    body: ReconcileRequest,
    current_user: User = Depends(get_current_user),
) -> ReconciliationReport:
    """
    Reconcile AIS vs Form 16 vs Capital Gains CSV.

    Flags discrepancies that could trigger IT department notices post-filing.
    Run this before generating ITR XML to catch undeclared income.

    Checks:
    - TDS from salary (Form 16 Part A vs AIS)
    - Interest income (AIS vs declared additional_income.interest_income)
    - Dividend income (AIS vs declared additional_income.other_income)
    - Securities/MF sale value (AIS vs broker CG CSV)
    - TDS on non-salary income (claim as TDS2 credit)

    Returns filing_risk: "low" | "medium" | "high".
    """
    return reconcile(
        form16=body.form16,
        ais=body.ais,
        additional_income=body.additional_income,
        capital_gains=body.capital_gains,
    )


@router.post("/generate-xml", response_model=ITRXMLResponse)
def generate_xml(
    body: ITRXMLRequest,
    current_user: User = Depends(get_current_user),
) -> ITRXMLResponse:
    """
    Generate ITR-1 or ITR-2 XML for manual upload to IT portal.

    ITR-1 (Sahaj): salary only, total income ≤ ₹50L, no capital gains.
    ITR-2: capital gains present, or house property income, or income > ₹50L.

    No ERI registration required — user uploads the returned XML at:
    incometax.gov.in → e-File → Income Tax Returns → File Income Tax Return
    → Online → Upload XML.

    Recommended workflow:
    1. POST /itr/form16/upload → get Form16Data
    2. POST /itr/capital-gains/upload → get CapitalGainsSummary (if applicable)
    3. POST /itr/ais/upload → get AISData
    4. POST /itr/reconcile → verify no undeclared income
    5. POST /itr/generate-xml → download and upload XML to portal
    """
    try:
        result = generate_itr_xml(body)
    except Exception as e:
        raise HTTPException(422, f"XML generation failed: {e}")
    return result
