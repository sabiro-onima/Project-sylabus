import uuid

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_coordinator, require_lecturer
from app.models.syllabus import Syllabus, SyllabusVersion
from app.models.user import User, UserRole
from app.schemas.syllabus import (
    SyllabusCreate,
    SyllabusFilter,
    SyllabusListResponse,
    SyllabusResponse,
    SyllabusVersionCreate,
    SyllabusVersionResponse,
    SyllabusVersionUpdate,
)
from app.services.syllabus_service import SyllabusService

router = APIRouter(prefix="/syllabi", tags=["syllabi"])


def _svc(db: AsyncSession = Depends(get_db)) -> SyllabusService:
    return SyllabusService(db)


# ─── HELPER: sprawdź czy użytkownik może edytować dany sylabuz ────────────────

async def _check_ownership(
    syllabus_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> Syllabus:
    """
    LECTURER może edytować tylko własne syllabusy.
    COORDINATOR i ADMIN mogą edytować wszystkie.
    STUDENT nie może edytować w ogóle.
    """
    if user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Studenci nie mogą edytować sylabusów.",
        )

    result = await db.execute(select(Syllabus).where(Syllabus.id == syllabus_id))
    syllabus = result.scalar_one_or_none()
    if not syllabus:
        raise HTTPException(status_code=404, detail="Sylabuz nie istnieje.")

    if user.role == UserRole.LECTURER and str(syllabus.author_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Możesz edytować tylko własne syllabusy.",
        )

    return syllabus


async def _check_version_ownership(
    version_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> SyllabusVersion:
    """Sprawdź ownership przez wersję syllabusa."""
    result = await db.execute(
        select(SyllabusVersion).where(SyllabusVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Wersja nie istnieje.")

    await _check_ownership(version.syllabus_id, user, db)
    return version


# ─── LISTA / FILTROWANIE — dostępne dla wszystkich zalogowanych ───────────────

@router.get("/", response_model=SyllabusListResponse)
async def list_syllabi(
    academic_year: str | None = None,
    academic_unit_id: uuid.UUID | None = None,
    status: str | None = None,
    course_type: str | None = None,
    semester_number: int | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
):
    filters = SyllabusFilter(
        academic_year=academic_year,
        academic_unit_id=academic_unit_id,
        status=status,
        course_type=course_type,
        semester_number=semester_number,
        search=search,
        page=page,
        size=size,
    )

    # Student widzi tylko zatwierdzone syllabusy
    if current_user.role == UserRole.STUDENT:
        filters.status = "approved"

    items, total = await svc.list_syllabi(filters)
    return SyllabusListResponse(items=items, total=total, page=page, size=size)


# ─── SIATKA PRZEDMIOTÓW — dostępne dla wszystkich zalogowanych ───────────────

@router.get("/grid")
async def subject_grid(
    academic_unit_id: uuid.UUID = Query(...),
    academic_year: str = Query(..., pattern=r"^\d{4}/\d{4}$"),
    svc: SyllabusService = Depends(_svc),
    _user: User = Depends(get_current_user),
):
    return await svc.get_subject_grid(academic_unit_id, academic_year)


# ─── TWORZENIE — tylko LECTURER, COORDINATOR, ADMIN ──────────────────────────

@router.post("/", response_model=SyllabusResponse, status_code=201)
async def create_syllabus(
    body: SyllabusCreate,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(require_lecturer),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Studenci nie mogą tworzyć sylabusów.")
    try:
        syllabus = await svc.create_syllabus(body, current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return syllabus


# ─── SZCZEGÓŁY — dostępne dla wszystkich, ale student widzi tylko zatwierdzone

@router.get("/{syllabus_id}", response_model=SyllabusResponse)
async def get_syllabus(
    syllabus_id: uuid.UUID,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
):
    try:
        syllabus = await svc.get_syllabus(syllabus_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Student widzi tylko zatwierdzone
    if current_user.role == UserRole.STUDENT:
        approved = [v for v in syllabus.versions if v.status == "approved"]
        if not approved:
            raise HTTPException(
                status_code=403,
                detail="Ten sylabuz nie jest jeszcze zatwierdzony.",
            )

    return syllabus


# ─── HISTORIA WERSJI — student widzi tylko zatwierdzone ──────────────────────

@router.get("/{syllabus_id}/versions", response_model=list[SyllabusVersionResponse])
async def version_history(
    syllabus_id: uuid.UUID,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
):
    versions = await svc.get_version_history(syllabus_id)

    # Student widzi tylko zatwierdzone wersje
    if current_user.role == UserRole.STUDENT:
        versions = [v for v in versions if v.status == "approved"]

    return versions


# ─── NOWA WERSJA — tylko właściciel / COORDINATOR / ADMIN ────────────────────

@router.post("/{syllabus_id}/versions", response_model=SyllabusVersionResponse, status_code=201)
async def new_version(
    syllabus_id: uuid.UUID,
    body: SyllabusVersionCreate,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_ownership(syllabus_id, current_user, db)
    try:
        return await svc.create_new_version(syllabus_id, body, current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── AKTUALIZACJA WERSJI — tylko właściciel / COORDINATOR / ADMIN ────────────

@router.patch("/versions/{version_id}", response_model=SyllabusVersionResponse)
async def update_version(
    version_id: uuid.UUID,
    body: SyllabusVersionUpdate,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_version_ownership(version_id, current_user, db)
    try:
        return await svc.update_version(version_id, body, current_user)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── HISTORIA ZMIAN ───────────────────────────────────────────────────────────

@router.get("/versions/{version_id}/changes")
async def version_changes(
    version_id: uuid.UUID,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
):
    # Student nie widzi historii zmian
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Studenci nie mają dostępu do historii zmian.",
        )
    try:
        return await svc.get_version_changes(version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── WORKFLOW: wysyłanie do zatwierdzenia — tylko właściciel ─────────────────

@router.post("/versions/{version_id}/submit")
async def submit_version(
    version_id: uuid.UUID,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_version_ownership(version_id, current_user, db)
    try:
        v = await svc.submit_for_approval(version_id, current_user)
        return {"status": v.status, "version_id": str(v.id)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── WORKFLOW: zatwierdzanie — tylko COORDINATOR / ADMIN ─────────────────────

@router.post("/versions/{version_id}/approve")
async def approve_version(
    version_id: uuid.UUID,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(require_coordinator),
):
    try:
        v = await svc.approve_version(version_id, current_user)
        return {"status": v.status, "version_id": str(v.id)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── WORKFLOW: odrzucanie — tylko COORDINATOR / ADMIN ────────────────────────

class RejectRequest(BaseModel):
    reason: str | None = None


@router.post("/versions/{version_id}/reject")
async def reject_version(
    version_id: uuid.UUID,
    body: RejectRequest = RejectRequest(),
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(require_coordinator),
):
    try:
        v = await svc.reject_version(version_id, current_user, body.reason)
        return {"status": v.status, "version_id": str(v.id)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── WORKFLOW: archiwizacja — tylko COORDINATOR / ADMIN ──────────────────────

@router.post("/versions/{version_id}/archive")
async def archive_version(
    version_id: uuid.UUID,
    svc: SyllabusService = Depends(_svc),
    current_user: User = Depends(require_coordinator),
):
    try:
        v = await svc.archive_version(version_id)
        return {"status": v.status, "version_id": str(v.id)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
