from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from uuid import UUID
import re
from app.models.business import ReturnFrequency


class BusinessCreate(BaseModel):
    legal_name: str
    gstin: str
    return_frequency: ReturnFrequency = ReturnFrequency.MONTHLY
    is_composition: bool = False

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str) -> str:
        pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid GSTIN format")
        return v.upper()


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    legal_name: str
    gstin: str
    state_code: str
    pan: str
    return_frequency: ReturnFrequency
    is_composition: bool
    created_at: datetime
