import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, DateTime, Enum as SAEnum, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class InvoiceType(str, enum.Enum):
    B2B = "b2b"
    B2C_LARGE = "b2c_large"
    B2C_SMALL = "b2c_small"
    EXPORT = "export"
    CREDIT_NOTE = "credit_note"


class InvoiceSource(str, enum.Enum):
    MANUAL = "manual"
    OCR_UPLOAD = "ocr_upload"
    IMPORT = "import"


class ITC2BStatus(str, enum.Enum):
    UNVERIFIED = "unverified"       # default — 2B recon not run yet
    MATCHED = "matched"             # appears in GSTR-2B → ITC claimable
    MISSING_IN_2B = "missing_in_2b" # not in 2B → ITC blocked per S.16(2)(aa)
    ACCEPTED_WITH_RISK = "accepted_with_risk"  # user override with risk acknowledgement


class OutwardInvoice(Base):
    __tablename__ = "outward_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    place_of_supply: Mapped[str] = mapped_column(String(2), nullable=False)  # state code
    invoice_type: Mapped[InvoiceType] = mapped_column(
        SAEnum(InvoiceType, values_callable=lambda x: [e.value for e in x]),
        default=InvoiceType.B2B,
    )
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    igst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cess: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    source: Mapped[InvoiceSource] = mapped_column(
        SAEnum(InvoiceSource, values_callable=lambda x: [e.value for e in x]),
        default=InvoiceSource.MANUAL,
    )
    hsn_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    raw_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class InwardInvoice(Base):
    __tablename__ = "inward_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    igst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    hsn_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_rcm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    itc_blocked_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    itc_2b_status: Mapped[ITC2BStatus] = mapped_column(
        SAEnum(ITC2BStatus, values_callable=lambda x: [e.value for e in x], name="itc2bstatus"),
        default=ITC2BStatus.UNVERIFIED,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
