"""
Academic units API endpoints.
  GET  /units/  – list all units (any authenticated user)
  POST /units/  – create unit (admin only)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import AcademicUnit, User

router = APIRouter(prefix="/units", tags=["units"])


class AcademicUnitResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    code: str
    parent_id: uuid.UUID | None = None


class AcademicUnitCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)
    parent_id: uuid.UUID | None = None


@router.get("/", response_model=list[AcademicUnitResponse])
async def list_units(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(AcademicUnit).order_by(AcademicUnit.name))
    return result.scalars().all()


@router.post("/", response_model=AcademicUnitResponse, status_code=201)
async def create_unit(
    body: AcademicUnitCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    existing = await db.execute(select(AcademicUnit).where(AcademicUnit.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Kod jednostki już istnieje.")
    unit = AcademicUnit(**body.model_dump())
    db.add(unit)
    await db.flush()
    return unit
