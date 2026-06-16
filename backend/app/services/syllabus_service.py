"""
Logika biznesowa sylabusów:
  - tworzenie / aktualizacja z automatycznym wersjonowaniem
  - śledzenie zmian (diff)
  - zatwierdzanie / odrzucanie wersji
  - walidacja godzin i ECTS
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.syllabus import (
    Syllabus,
    SyllabusChange,
    SyllabusStatus,
    SyllabusVersion,
)
from app.models.user import User
from app.schemas.syllabus import (
    SyllabusCreate,
    SyllabusFilter,
    SyllabusVersionCreate,
    SyllabusVersionUpdate,
)


class SyllabusService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── CREATE ──────────────────────────────────────────────────────────────

    async def create_syllabus(self, data: SyllabusCreate, author: User) -> Syllabus:
        syllabus = Syllabus(
            course_code=data.course_code,
            academic_unit_id=data.academic_unit_id,
            author_id=author.id,
        )
        self.db.add(syllabus)
        await self.db.flush()

        await self._create_version(
            syllabus_id=syllabus.id,
            data=data.initial_version,
            user=author,
            version_number=1,
        )
        result = await self.db.execute(
            select(Syllabus)
            .options(selectinload(Syllabus.versions))
            .where(Syllabus.id == syllabus.id)
        )
        return result.scalar_one()

    # ─── NEW VERSION ─────────────────────────────────────────────────────────

    async def create_new_version(
        self,
        syllabus_id: uuid.UUID,
        data: SyllabusVersionCreate,
        user: User,
    ) -> SyllabusVersion:
        # Pobierz najwyższy numer wersji
        result = await self.db.execute(
            select(func.max(SyllabusVersion.version_number)).where(
                SyllabusVersion.syllabus_id == syllabus_id
            )
        )
        max_version = result.scalar() or 0
        return await self._create_version(
            syllabus_id=syllabus_id,
            data=data,
            user=user,
            version_number=max_version + 1,
        )

    # ─── UPDATE EXISTING VERSION (only DRAFT) ────────────────────────────────

    async def update_version(
        self,
        version_id: uuid.UUID,
        data: SyllabusVersionUpdate,
        user: User,
    ) -> SyllabusVersion:
        version = await self._get_version_or_raise(version_id)

        if version.status != SyllabusStatus.DRAFT:
            raise ValueError("Można edytować tylko wersje w stanie DRAFT.")

        update_data = data.model_dump(exclude_unset=True)
        changes = self._compute_diff(version, update_data, user)

        for field, value in update_data.items():
            # JSONB fields – serialize to plain list/dict
            if hasattr(value, "model_dump"):
                value = [v.model_dump() for v in value] if isinstance(value, list) else value.model_dump()
            elif isinstance(value, list) and value and hasattr(value[0], "model_dump"):
                value = [v.model_dump() for v in value]
            setattr(version, field, value)

        self.db.add_all(changes)
        await self.db.flush()
        # reload_after_update: eager-load to avoid lazy-load during serialization
        result = await self.db.execute(
            select(SyllabusVersion).where(SyllabusVersion.id == version.id)
        )
        return result.scalar_one()

    # ─── STATUS TRANSITIONS ──────────────────────────────────────────────────

    async def submit_for_approval(self, version_id: uuid.UUID, user: User) -> SyllabusVersion:
        version = await self._get_version_or_raise(version_id)
        if version.status != SyllabusStatus.DRAFT:
            raise ValueError("Tylko wersja DRAFT może być wysłana do zatwierdzenia.")
        version.status = SyllabusStatus.PENDING
        return version

    async def approve_version(self, version_id: uuid.UUID, approver: User) -> SyllabusVersion:
        version = await self._get_version_or_raise(version_id)
        if version.status != SyllabusStatus.PENDING:
            raise ValueError("Tylko wersja PENDING może być zatwierdzona.")
        version.status = SyllabusStatus.APPROVED
        version.approved_by_id = approver.id
        return version

    async def reject_version(
        self,
        version_id: uuid.UUID,
        reviewer: User,
        reason: str | None = None,
    ) -> SyllabusVersion:
        version = await self._get_version_or_raise(version_id)
        if version.status != SyllabusStatus.PENDING:
            raise ValueError("Tylko wersja PENDING może być odrzucona.")
        version.status = SyllabusStatus.DRAFT
        if reason:
            version.changelog_note = f"[Odrzucono: {reason}]"
        return version

    async def archive_version(self, version_id: uuid.UUID) -> SyllabusVersion:
        version = await self._get_version_or_raise(version_id)
        version.status = SyllabusStatus.ARCHIVED
        return version

    # ─── READ ────────────────────────────────────────────────────────────────

    async def list_syllabi(self, filters: SyllabusFilter) -> tuple[list[Syllabus], int]:
        query = (
            select(Syllabus)
            .options(
                selectinload(Syllabus.versions),
                selectinload(Syllabus.academic_unit),
            )
            .where(Syllabus.is_active == True)
        )

        if filters.academic_unit_id:
            query = query.where(Syllabus.academic_unit_id == filters.academic_unit_id)

        if filters.search:
            term = f"%{filters.search}%"
            # Join z SyllabusVersion do szukania po tytule
            query = query.join(Syllabus.versions).where(
                or_(
                    Syllabus.course_code.ilike(term),
                    SyllabusVersion.title_pl.ilike(term),
                    SyllabusVersion.title_en.ilike(term),
                )
            )

        if filters.course_type:
            query = query.join(Syllabus.versions).where(
                SyllabusVersion.course_type == filters.course_type
            )

        if filters.semester_number:
            query = query.join(Syllabus.versions).where(
                SyllabusVersion.semester_number == filters.semester_number
            )

        if filters.status:
            query = query.join(Syllabus.versions).where(
                SyllabusVersion.status == filters.status
            )

        if filters.academic_year:
            query = query.join(Syllabus.versions).where(
                SyllabusVersion.academic_year == filters.academic_year
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar()

        query = query.offset((filters.page - 1) * filters.size).limit(filters.size)
        result = await self.db.execute(query)
        return result.scalars().unique().all(), total

    async def get_syllabus(self, syllabus_id: uuid.UUID) -> Syllabus:
        result = await self.db.execute(
            select(Syllabus)
            .options(
                selectinload(Syllabus.versions).selectinload(SyllabusVersion.changes),
                selectinload(Syllabus.academic_unit),
                selectinload(Syllabus.author),
            )
            .where(Syllabus.id == syllabus_id)
        )
        s = result.scalar_one_or_none()
        if not s:
            raise ValueError("Syllabus nie istnieje.")
        return s

    async def get_version_history(self, syllabus_id: uuid.UUID) -> list[SyllabusVersion]:
        result = await self.db.execute(
            select(SyllabusVersion)
            .where(SyllabusVersion.syllabus_id == syllabus_id)
            .options(selectinload(SyllabusVersion.created_by))
            .order_by(SyllabusVersion.version_number.desc())
        )
        return result.scalars().all()

    # ─── SUBJECT GRID (siatka przedmiotów) ───────────────────────────────────

    async def get_subject_grid(
        self,
        academic_unit_id: uuid.UUID,
        academic_year: str,
    ) -> dict[int, list[dict]]:
        """
        Zwraca siatkę przedmiotów pogrupowaną po semestrach.
        {1: [{code, title, hours_total, ects, ...}], 2: [...], ...}
        """
        result = await self.db.execute(
            select(Syllabus, SyllabusVersion)
            .join(Syllabus.versions)
            .where(
                Syllabus.academic_unit_id == academic_unit_id,
                SyllabusVersion.academic_year == academic_year,
                SyllabusVersion.status == SyllabusStatus.APPROVED,
            )
            .order_by(SyllabusVersion.semester_number, Syllabus.course_code)
        )

        grid: dict[int, list[dict]] = {}
        for syllabus, version in result.all():
            sem = version.semester_number
            grid.setdefault(sem, []).append({
                "course_code": syllabus.course_code,
                "title_pl": version.title_pl,
                "course_type": version.course_type,
                "semester": version.semester,
                "ects_credits": float(version.ects_credits),
                "hours_lecture": version.hours_lecture,
                "hours_laboratory": version.hours_laboratory,
                "hours_exercise": version.hours_exercise,
                "total_hours": version.total_hours,
            })
        return grid

    # ─── PRIVATE HELPERS ─────────────────────────────────────────────────────

    async def _create_version(
        self,
        syllabus_id: uuid.UUID,
        data: SyllabusVersionCreate,
        user: User,
        version_number: int,
    ) -> SyllabusVersion:
        version = SyllabusVersion(
            syllabus_id=syllabus_id,
            version_number=version_number,
            created_by_id=user.id,
            **{
                k: (
                    [item.model_dump() for item in v]
                    if isinstance(v, list) and v and hasattr(v[0], "model_dump")
                    else v
                )
                for k, v in data.model_dump().items()
            },
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def _get_version_or_raise(self, version_id: uuid.UUID) -> SyllabusVersion:
        result = await self.db.execute(
            select(SyllabusVersion).where(SyllabusVersion.id == version_id)
        )
        v = result.scalar_one_or_none()
        if not v:
            raise ValueError("Wersja syllabusa nie istnieje.")
        return v

    def _compute_diff(
        self,
        version: SyllabusVersion,
        update_data: dict,
        user: User,
    ) -> list[SyllabusChange]:
        changes = []
        now = datetime.utcnow()  # naive — matches TIMESTAMP WITHOUT TIME ZONE in DB
        for field, new_value in update_data.items():
            old_value = getattr(version, field, None)
            if old_value != new_value:
                changes.append(
                    SyllabusChange(
                        version_id=version.id,
                        user_id=user.id,
                        changed_at=now,
                        field_name=field,
                        old_value={"value": old_value} if not isinstance(old_value, (dict, list)) else old_value,
                        new_value={"value": new_value} if not isinstance(new_value, (dict, list)) else new_value,
                        change_type="update",
                    )
                )
        return changes
