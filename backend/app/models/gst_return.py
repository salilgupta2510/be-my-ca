import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Numeric, DateTime, Enum as SAEnum, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ReturnType(str, enum.Enum):
    GSTR1 = "gstr1"
    GSTR3B = "gstr3b"
    GSTR4 = "gstr4"


class ReturnStatus(str, enum.Enum):
    DRAFT = "draft"
    READY_TO_FILE = "ready_to_file"
    FILED = "filed"
    FILING_FAILED = "filing_failed"


class GSTReturn(Base):
    __tablename__ = "gst_returns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    return_type: Mapped[ReturnType] = mapped_column(
        SAEnum(ReturnType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, values_callable=lambda x: [e.value for e in x]),
        default=ReturnStatus.DRAFT,
    )
    computed_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    total_tax_payable: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    itc_claimed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    arn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
