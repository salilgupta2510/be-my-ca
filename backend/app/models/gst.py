import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, DateTime, Enum as SAEnum, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "matched"
    MISSING_IN_2B = "missing_in_2b"
    MISSING_IN_BOOKS = "missing_in_books"
    AMOUNT_MISMATCH = "amount_mismatch"
    TAX_RATE_MISMATCH = "tax_rate_mismatch"
    DUPLICATE = "duplicate"
    PENDING_IMS = "pending_ims"


class IMSAction(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    PENDING = "pending"


class GSTR2BRecord(Base):
    __tablename__ = "gstr2b_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    supplier_gstin: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    igst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    cgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    sgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    ims_action: Mapped[IMSAction] = mapped_column(SAEnum(IMSAction, values_callable=lambda x: [e.value for e in x]), default=IMSAction.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PurchaseRegisterRecord(Base):
    __tablename__ = "purchase_register_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    igst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    cgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    sgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual, tally, zoho
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    gstr2b_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("gstr2b_records.id"), nullable=True)
    inward_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("inward_invoices.id"), nullable=True)
    status: Mapped[ReconciliationStatus] = mapped_column(SAEnum(ReconciliationStatus, values_callable=lambda x: [e.value for e in x]), nullable=False)
    match_confidence: Mapped[int] = mapped_column(Integer, default=100)  # 0-100
    taxable_diff: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    tax_diff: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
