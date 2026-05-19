import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum as SAEnum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ReturnFrequency(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True, unique=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    pan: Mapped[str] = mapped_column(String(10), nullable=False)
    return_frequency: Mapped[ReturnFrequency] = mapped_column(
        SAEnum(ReturnFrequency, values_callable=lambda x: [e.value for e in x]),
        default=ReturnFrequency.MONTHLY,
    )
    is_composition: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
