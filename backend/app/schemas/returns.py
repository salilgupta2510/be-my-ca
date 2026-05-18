from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from app.models.gst_return import ReturnType, ReturnStatus


class GSTReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    period: str
    return_type: ReturnType
    status: ReturnStatus
    computed_payload: dict | None
    total_tax_payable: Decimal
    itc_claimed: Decimal
    arn: str | None
    filed_at: datetime | None
    created_at: datetime
