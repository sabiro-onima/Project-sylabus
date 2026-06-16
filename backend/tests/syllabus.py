import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.syllabus import CourseType, Semester, SyllabusStatus


# ─── LEARNING OUTCOMES ───────────────────────────────────────────────────────

class LearningOutcome(BaseModel):
    code: str = Field(max_length=20)
    description: str
    category: str  # knowledge | skills | competences


# ─── ASSESSMENT METHOD ───────────────────────────────────────────────────────

class AssessmentMethod(BaseModel):
    method: str           # exam | project | quiz | report | presentation | attendance
    weight: int = Field(ge=0, le=100)
    description: str | None = None


# ─── BIBLIOGRAPHY ────────────────────────────────────────────────────────────

class BibliographyItem(BaseModel):
    type: str             # primary | supplementary
    citation: str
    url: str | None = None


# ─── SYLLABUS VERSION (write) ─────────────────────────────────────────────────

class SyllabusVersionCreate(BaseModel):
    title_pl: str = Field(min_length=3, max_length=255)
    title_en: str | None = Field(default=None, max_length=255)
    course_type: CourseType
    semester: Semester
    semester_number: int = Field(ge=1, le=12)
    ects_credits: float = Field(gt=0, le=30)
    language: str = Field(default="pl", max_length=10)

    description: str | None = None
    learning_objectives: str | None = None
    prerequisites: str | None = None

    learning_outcomes: list[LearningOutcome] = Field(default_factory=list)

    hours_lecture: int = Field(default=0, ge=0)
    hours_laboratory: int = Field(default=0, ge=0)
    hours_exercise: int = Field(default=0, ge=0)
    hours_seminar: int = Field(default=0, ge=0)
    hours_project: int = Field(default=0, ge=0)
    hours_self_study: int = Field(default=0, ge=0)

    assessment_methods: list[AssessmentMethod] = Field(default_factory=list)
    bibliography: list[BibliographyItem] = Field(default_factory=list)
    changelog_note: str | None = None

    academic_year: str = Field(
        pattern=r"^\d{4}/\d{4}$",
        description="Format: 2024/2025",
    )

    @field_validator("academic_year")
    @classmethod
    def validate_academic_year(cls, v: str) -> str:
        start, end = v.split("/")
        if int(end) != int(start) + 1:
            raise ValueError("Rok akademicki musi być kolejnym rokiem, np. 2024/2025.")
        return v

    @model_validator(mode="after")
    def validate_assessment_weights(self) -> "SyllabusVersionCreate":
        if self.assessment_methods:
            total = sum(m.weight for m in self.assessment_methods)
            if total != 100:
                raise ValueError(
                    f"Suma wag metod oceniania musi wynosić 100% (aktualnie: {total}%)."
                )
        return self

    @model_validator(mode="after")
    def validate_total_hours(self) -> "SyllabusVersionCreate":
        contact = (
            self.hours_lecture
            + self.hours_laboratory
            + self.hours_exercise
            + self.hours_seminar
            + self.hours_project
        )
        total = contact + self.hours_self_study
        # ECTS: 1 punkt = 25–30 godzin
        min_hours = int(self.ects_credits * 25)
        max_hours = int(self.ects_credits * 30)
        if total < min_hours or total > max_hours:
            raise ValueError(
                f"Całkowita liczba godzin ({total}) nie odpowiada ECTS ({self.ects_credits}). "
                f"Oczekiwany zakres: {min_hours}–{max_hours} godzin."
            )
        return self


class SyllabusVersionUpdate(BaseModel):
    """
    Wszystkie pola opcjonalne przy aktualizacji (PATCH).

    WAŻNE: dziedziczymy z BaseModel, NIE z SyllabusVersionCreate,
    żeby walidatory validate_total_hours i validate_assessment_weights
    nie strzelały na None gdy pole nie zostało podane w żądaniu.
    Walidacja uruchamia się tylko gdy dane pola są obecne.
    """
    title_pl: str | None = Field(default=None, min_length=3, max_length=255)
    title_en: str | None = Field(default=None, max_length=255)
    course_type: CourseType | None = None
    semester: Semester | None = None
    semester_number: int | None = Field(default=None, ge=1, le=12)
    ects_credits: float | None = Field(default=None, gt=0, le=30)
    language: str | None = Field(default=None, max_length=10)

    description: str | None = None
    learning_objectives: str | None = None
    prerequisites: str | None = None

    learning_outcomes: list[LearningOutcome] | None = None

    hours_lecture: int | None = Field(default=None, ge=0)
    hours_laboratory: int | None = Field(default=None, ge=0)
    hours_exercise: int | None = Field(default=None, ge=0)
    hours_seminar: int | None = Field(default=None, ge=0)
    hours_project: int | None = Field(default=None, ge=0)
    hours_self_study: int | None = Field(default=None, ge=0)

    assessment_methods: list[AssessmentMethod] | None = None
    bibliography: list[BibliographyItem] | None = None
    changelog_note: str | None = None

    academic_year: str | None = Field(
        default=None,
        pattern=r"^\d{4}/\d{4}$",
        description="Format: 2024/2025",
    )

    @field_validator("academic_year", mode="before")
    @classmethod
    def validate_academic_year(cls, v: str | None) -> str | None:
        if v is None:
            return v
        start, end = v.split("/")
        if int(end) != int(start) + 1:
            raise ValueError("Rok akademicki musi być kolejnym rokiem, np. 2024/2025.")
        return v

    @model_validator(mode="after")
    def validate_assessment_weights(self) -> "SyllabusVersionUpdate":
        if self.assessment_methods is not None:
            total = sum(m.weight for m in self.assessment_methods)
            if total != 100:
                raise ValueError(
                    f"Suma wag metod oceniania musi wynosić 100% (aktualnie: {total}%)."
                )
        return self


# ─── SYLLABUS (write) ─────────────────────────────────────────────────────────

class SyllabusCreate(BaseModel):
    course_code: str = Field(min_length=2, max_length=50)
    academic_unit_id: uuid.UUID
    initial_version: SyllabusVersionCreate


# ─── RESPONSES (read) ────────────────────────────────────────────────────────

class SyllabusVersionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    syllabus_id: uuid.UUID
    version_number: int
    academic_year: str
    status: SyllabusStatus
    title_pl: str
    title_en: str | None
    course_type: CourseType
    semester: Semester
    semester_number: int
    ects_credits: float
    language: str
    description: str | None
    learning_objectives: str | None
    prerequisites: str | None
    learning_outcomes: list[Any]
    hours_lecture: int
    hours_laboratory: int
    hours_exercise: int
    hours_seminar: int
    hours_project: int
    hours_self_study: int
    assessment_methods: list[Any]
    bibliography: list[Any]
    changelog_note: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def total_hours(self) -> int:
        return (
            self.hours_lecture + self.hours_laboratory + self.hours_exercise
            + self.hours_seminar + self.hours_project + self.hours_self_study
        )


class SyllabusResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    course_code: str
    academic_unit_id: uuid.UUID
    author_id: uuid.UUID
    is_active: bool
    created_at: datetime
    latest_version: SyllabusVersionResponse | None = None


class SyllabusListResponse(BaseModel):
    items: list[SyllabusResponse]
    total: int
    page: int
    size: int


# ─── FILTERS ─────────────────────────────────────────────────────────────────

class SyllabusFilter(BaseModel):
    academic_year: str | None = None
    academic_unit_id: uuid.UUID | None = None
    status: SyllabusStatus | None = None
    course_type: CourseType | None = None
    semester_number: int | None = None
    search: str | None = None   # szuka po tytule i kodzie
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
