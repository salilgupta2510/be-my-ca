from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.models.waitlist import WaitlistEntry

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistIn(BaseModel):
    email: EmailStr
    name: str | None = None


@router.post("", status_code=201)
async def join_waitlist(payload: WaitlistIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == payload.email))
    if result.scalar_one_or_none():
        return {"message": "You're already on the list!", "already_registered": True}
    entry = WaitlistEntry(email=payload.email, name=payload.name)
    db.add(entry)
    await db.flush()
    return {"message": "You're on the list!", "already_registered": False}
