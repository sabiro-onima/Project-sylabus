"""
Endpointy programów studiów (kierunków):
  GET    /programs/                      – lista programów
  POST   /programs/                      – utwórz program (admin/coordinator)
  GET    /programs/{program_id}          – szczegóły
  PATCH  /programs/{program_id}          – edytuj (admin/coordinator)
  DELETE /programs/{program_id}          – usuń (admin)
  GET    /programs/{program_id}/syllabi  – lista sylabusów przypisanych do programu
  POST   /programs/{program_id}/syllabi/{syllabus_id}  – przypisz sylabus
  DELETE /programs/{program_id}/syllabi/{syllabus_id}  – odepnij sylabus
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_coordinator
from app.models.syllabus import StudyProgram, Syllabus, syllabus_program_links
from app.models.user import User

router = APIRouter(prefix="/programs", tags=["programs"])


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class StudyProgramCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=2, max_length=50)
    degree: str = Field(description="bachelor / master / phd")
    form: str = Field(description="full-time / part-time")
    duration_semesters: int = Field(default=7, ge=1, le=20)
    academic_unit_id: uuid.UUID


class StudyProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    degree: str | None = None
    form: str | None = None
    duration_semesters: int | None = Field(default=None, ge=1, le=20)


class StudyProgramResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    code: str
    degree: str
    form: str
    duration_semesters: int
    academic_unit_id: uuid.UUID


class SyllabusProgramLink(BaseModel):
    semester_number: int = Field(ge=1, le=12)


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[StudyProgramResponse])
async def list_programs(
    academic_unit_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = select(StudyProgram)
    if academic_unit_id:
        q = q.where(StudyProgram.academic_unit_id == academic_unit_id)
    result = await db.execute(q.order_by(StudyProgram.name))
    return result.scalars().all()


@router.post("/", response_model=StudyProgramResponse, status_code=201)
async def create_program(
    body: StudyProgramCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_coordinator),
):
    existing = await db.execute(select(StudyProgram).where(StudyProgram.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Kod programu już istnieje.")
    program = StudyProgram(**body.model_dump())
    db.add(program)
    await db.flush()
    return program


@router.get("/{program_id}", response_model=StudyProgramResponse)
async def get_program(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(StudyProgram).where(StudyProgram.id == program_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Program nie istnieje.")
    return p


@router.patch("/{program_id}", response_model=StudyProgramResponse)
async def update_program(
    program_id: uuid.UUID,
    body: StudyProgramUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_coordinator),
):
    result = await db.execute(select(StudyProgram).where(StudyProgram.id == program_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Program nie istnieje.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    await db.flush()
    return p


@router.delete("/{program_id}", status_code=204)
async def delete_program(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_coordinator),
):
    result = await db.execute(select(StudyProgram).where(StudyProgram.id == program_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Program nie istnieje.")
    await db.delete(p)


# ─── SYLLABUS ↔ PROGRAM LINKS ─────────────────────────────────────────────────

@router.get("/{program_id}/syllabi")
async def list_program_syllabi(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Zwraca sylabusy przypisane do programu z numerem semestru."""
    result = await db.execute(
        select(Syllabus, syllabus_program_links.c.semester_number)
        .join(syllabus_program_links, syllabus_program_links.c.syllabus_id == Syllabus.id)
        .where(syllabus_program_links.c.program_id == program_id)
        .order_by(syllabus_program_links.c.semester_number, Syllabus.course_code)
    )
    rows = result.all()
    return [
        {"syllabus_id": str(s.id), "course_code": s.course_code, "semester_number": sem}
        for s, sem in rows
    ]


@router.post("/{program_id}/syllabi/{syllabus_id}", status_code=201)
async def link_syllabus(
    program_id: uuid.UUID,
    syllabus_id: uuid.UUID,
    body: SyllabusProgramLink,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_coordinator),
):
    """Przypisuje sylabus do programu na danym semestrze."""
    await db.execute(
        syllabus_program_links.insert().values(
            syllabus_id=syllabus_id,
            program_id=program_id,
            semester_number=body.semester_number,
        )
    )
    return {"status": "linked"}


@router.delete("/{program_id}/syllabi/{syllabus_id}", status_code=204)
async def unlink_syllabus(
    program_id: uuid.UUID,
    syllabus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_coordinator),
):
    """Odpina sylabus od programu."""
    await db.execute(
        delete(syllabus_program_links).where(
            syllabus_program_links.c.program_id == program_id,
            syllabus_program_links.c.syllabus_id == syllabus_id,
        )
    )
