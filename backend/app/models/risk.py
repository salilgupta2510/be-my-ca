import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Numeric, DateTime, Enum as SAEnum, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    financial_year: Mapped[str] = mapped_column(String(7), nullable=False)  # 2025-26
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    risk_level: Mapped[RiskLevel] = mapped_column(SAEnum(RiskLevel, values_callable=lambda x: [e.value for e in x]), nullable=False)
    risk_factors: Mapped[dict] = mapped_column(JSON, default=list)  # list of {factor, score, description, advice}
    declared_income: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # salary, business, investment, etc.
    is_high_value_cash: Mapped[bool] = mapped_column(default=False)
    source_bank: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
