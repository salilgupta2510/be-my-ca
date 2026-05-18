from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from app.core.database import get_db
from app.models.risk import RiskScore, BankTransaction, RiskLevel
from app.models.gst import ReconciliationResult, ReconciliationStatus
from app.services.risk_engine import compute_risk_score
from app.services.ocr_service import parse_bank_statement
from app.api.deps import get_current_user
from app.models.user import User
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/bank-statement/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    bank: str = Query(default="unknown"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    transactions = await parse_bank_statement(content, file.filename, bank)

    for txn in transactions:
        is_cash = "CASH" in txn["description"].upper() and txn.get("credit", 0) > 0
        record = BankTransaction(
            user_id=current_user.id,
            transaction_date=datetime.now(timezone.utc),
            description=txn["description"],
            debit=Decimal(str(txn.get("debit", 0))),
            credit=Decimal(str(txn.get("credit", 0))),
            balance=Decimal(str(txn.get("balance", 0))),
            is_high_value_cash=is_cash and txn.get("credit", 0) > 200000,
            source_bank=bank,
        )
        db.add(record)

    return {"status": "uploaded", "transactions_parsed": len(transactions)}


@router.post("/compute/{financial_year}")
async def compute_risk(
    financial_year: str,
    declared_income: Decimal = Query(..., description="Total declared income for the FY"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bank_txns = (await db.scalars(
        select(BankTransaction).where(BankTransaction.user_id == current_user.id)
    )).all()

    total_cash = sum(t.debit + t.credit for t in bank_txns if t.is_high_value_cash)
    total_hvp = Decimal("0")
    total_credits = sum(t.credit for t in bank_txns)

    gst_mismatches = await db.scalar(
        select(ReconciliationResult)
        .where(
            ReconciliationResult.user_id == current_user.id,
            ReconciliationResult.status != ReconciliationStatus.MATCHED,
            ReconciliationResult.resolved == False,
        )
    ) or 0

    report = compute_risk_score(
        declared_income=declared_income,
        total_cash_deposits=Decimal(str(total_cash)),
        total_high_value_purchases=total_hvp,
        total_credits=Decimal(str(total_credits)),
        gst_mismatch_count=int(gst_mismatches) if gst_mismatches else 0,
        itc_reversal_risk_amount=Decimal("0"),
    )

    risk_record = RiskScore(
        user_id=current_user.id,
        financial_year=financial_year,
        overall_score=report.overall_score,
        risk_level=RiskLevel(report.level),
        risk_factors=report.factors,
        declared_income=declared_income,
    )
    db.add(risk_record)

    return {
        "financial_year": financial_year,
        "overall_score": report.overall_score,
        "level": report.level,
        "level_color": report.level_color,
        "factors": report.factors,
    }


@router.get("/latest")
async def get_latest_risk(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await db.scalar(
        select(RiskScore)
        .where(RiskScore.user_id == current_user.id)
        .order_by(RiskScore.computed_at.desc())
    )
    if not record:
        return {"message": "No risk score computed yet. Upload bank statement first."}
    return {
        "overall_score": record.overall_score,
        "level": record.risk_level.value,
        "factors": record.risk_factors,
        "computed_at": record.computed_at,
    }
