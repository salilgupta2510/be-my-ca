from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.business import Business
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessOut
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/business", tags=["business"])


def _derive_state_pan(gstin: str) -> tuple[str, str]:
    state_code = gstin[:2]
    pan = gstin[2:12]
    return state_code, pan


@router.post("", response_model=BusinessOut, status_code=200)
async def create_business(
    body: BusinessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    state_code, pan = _derive_state_pan(body.gstin)
    existing = await db.scalar(select(Business).where(Business.user_id == current_user.id))
    if existing:
        existing.legal_name = body.legal_name
        existing.gstin = body.gstin
        existing.state_code = state_code
        existing.pan = pan
        existing.return_frequency = body.return_frequency
        await db.commit()
        await db.refresh(existing)
        return existing

    business = Business(
        id=uuid.uuid4(),
        user_id=current_user.id,
        legal_name=body.legal_name,
        gstin=body.gstin,
        state_code=state_code,
        pan=pan,
        return_frequency=body.return_frequency,
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


@router.get("/me", response_model=BusinessOut)
async def get_my_business(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await db.scalar(select(Business).where(Business.user_id == current_user.id))
    if not business:
        raise HTTPException(404, "No business registered. Complete onboarding first.")
    return business
