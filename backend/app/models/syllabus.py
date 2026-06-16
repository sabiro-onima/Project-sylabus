"""
Modele sylabusów z pełnym wersjonowaniem.

Architektura wersjonowania:
  Syllabus        – "master record" przedmiotu (niezmienny identyfikator)
  SyllabusVersion – konkretna wersja syllabusa (np. 2024/2025)
  SyllabusChange  – historia każdej zmiany w danej wersji
"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SyllabusStatus(str, Enum):
    DRAFT = "draft"           # robocza
    PENDING = "pending"       # czeka na zatwierdzenie
    APPROVED = "approved"     # zatwierdzona
    ARCHIVED = "archived"     # archiwalna


class Semester(str, Enum):
    WINTER = "winter"         # semestr zimowy
    SUMMER = "summer"         # semestr letni


class CourseType(str, Enum):
    LECTURE = "lecture"               # wykład
    LABORATORY = "laboratory"         # laboratorium
    EXERCISE = "exercise"             # ćwiczenia
    SEMINAR = "seminar"               # seminarium
    PROJECT = "project"               # projekt
    PRACTICUM = "practicum"           # praktyki


# ─── PROGRAM STUDIÓW ────────────────────────────────────────────────────────

class StudyProgram(Base):
    """Program studiów (kierunek + stopień + forma)."""
    __tablename__ = "study_programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    degree: Mapped[str] = mapped_column(String(50), nullable=False)   # bachelor / master / phd
    form: Mapped[str] = mapped_column(String(50), nullable=False)     # full-time / part-time
    duration_semesters: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    academic_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id"), nullable=False
    )
    academic_unit: Mapped["AcademicUnit"] = relationship()
    syllabi: Mapped[list["Syllabus"]] = relationship(
        secondary="syllabus_program_links", back_populates="study_programs"
    )


# ─── PRZEDMIOT (master record) ───────────────────────────────────────────────

class Syllabus(Base):
    """
    Przedmiot w systemie. Jeden rekord na przedmiot.
    Właściwa treść przechowywana w SyllabusVersion.
    """
    __tablename__ = "syllabi"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    academic_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    academic_unit: Mapped["AcademicUnit"] = relationship(back_populates="syllabi")
    author: Mapped["User"] = relationship(back_populates="syllabi")
    versions: Mapped[list["SyllabusVersion"]] = relationship(
        back_populates="syllabus", order_by="SyllabusVersion.version_number.desc()"
    )
    study_programs: Mapped[list[StudyProgram]] = relationship(
        secondary="syllabus_program_links", back_populates="syllabi"
    )

    __table_args__ = (
        UniqueConstraint("course_code", "academic_unit_id", name="uq_course_unit"),
    )

    @property
    def latest_version(self):
        if not self.versions:
            return None
        return max(self.versions, key=lambda v: v.version_number)

    def __repr__(self) -> str:
        return f"<Syllabus {self.course_code}>"


class SyllabusVersion(Base):
    """
    Konkretna wersja syllabusa (np. rok akademicki 2024/2025).
    Zawiera całą treść: opis, cele, efekty, godziny, literaturę itd.
    """
    __tablename__ = "syllabus_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    syllabus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("syllabi.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)  # "2024/2025"
    status: Mapped[SyllabusStatus] = mapped_column(
        String(50), nullable=False, default=SyllabusStatus.DRAFT
    )

    # ── Podstawowe informacje ────────────────────────────────────────────────
    title_pl: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    course_type: Mapped[CourseType] = mapped_column(String(50), nullable=False)
    semester: Mapped[Semester] = mapped_column(String(20), nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–10 (do siatki)
    ects_credits: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="pl")

    # ── Treść syllabusa ─────────────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Efekty kształcenia (lista JSON)
    # [{code: "EK1", description: "...", category: "knowledge|skills|competences"}]
    learning_outcomes: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # ── Godziny (walidacja: suma == total_hours) ─────────────────────────────
    hours_lecture: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_laboratory: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_exercise: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_seminar: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_project: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_self_study: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # total_hours = suma wszystkich powyższych (sprawdzane przez CHECK + serwis)

    # ── Metody i ocenianie ───────────────────────────────────────────────────
    # [{method: "exam|project|...", weight: 60, description: "..."}]
    assessment_methods: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # ── Literatura ───────────────────────────────────────────────────────────
    # [{type: "primary|supplementary", citation: "...", url: "..."}]
    bibliography: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # ── Metadane wersji ──────────────────────────────────────────────────────
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changelog_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    syllabus: Mapped[Syllabus] = relationship(back_populates="versions")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    approved_by: Mapped["User | None"] = relationship(foreign_keys=[approved_by_id])
    changes: Mapped[list["SyllabusChange"]] = relationship(
        back_populates="version", order_by="SyllabusChange.changed_at.desc()"
    )

    __table_args__ = (
        UniqueConstraint(
            "syllabus_id", "academic_year", "version_number",
            name="uq_syllabus_year_version"
        ),
        CheckConstraint("ects_credits > 0", name="ck_ects_positive"),
        CheckConstraint("semester_number BETWEEN 1 AND 12", name="ck_semester_range"),
    )

    @property
    def total_hours(self) -> int:
        return (
            self.hours_lecture
            + self.hours_laboratory
            + self.hours_exercise
            + self.hours_seminar
            + self.hours_project
            + self.hours_self_study
        )

    @property
    def contact_hours(self) -> int:
        """Godziny kontaktowe (bez samodzielnej nauki)."""
        return (
            self.hours_lecture
            + self.hours_laboratory
            + self.hours_exercise
            + self.hours_seminar
            + self.hours_project
        )

    def __repr__(self) -> str:
        return f"<SyllabusVersion {self.syllabus_id} v{self.version_number} [{self.academic_year}]>"


class SyllabusChange(Base):
    """
    Historia każdej zmiany w wersji syllabusa.
    Przechowuje diff JSON: co było przed zmianą i po zmianie.
    """
    __tablename__ = "syllabus_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("syllabus_versions.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    changed_at: Mapped["datetime"] = mapped_column(nullable=False)

    # Jakie pole zostało zmienione
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # create/update/delete

    # Relationships
    version: Mapped[SyllabusVersion] = relationship(back_populates="changes")
    user: Mapped["User"] = relationship()


# ─── TABELA ŁĄCZĄCA: sylabus ↔ program studiów ───────────────────────────────

from sqlalchemy import Table, Column

syllabus_program_links = Table(
    "syllabus_program_links",
    Base.metadata,
    Column("syllabus_id", UUID(as_uuid=True), ForeignKey("syllabi.id"), primary_key=True),
    Column("program_id", UUID(as_uuid=True), ForeignKey("study_programs.id"), primary_key=True),
    Column("semester_number", Integer, nullable=False),  # na którym semestrze
)


# ─── AUDIT LOG ───────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Ogólny log wszystkich akcji w systemie."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # create_syllabus, approve_version…
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")
