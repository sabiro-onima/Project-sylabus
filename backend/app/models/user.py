import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, Enum):
    ADMIN = "admin"           # zarządza całym systemem
    COORDINATOR = "coordinator"  # zarządza sylabusami wydziału
    LECTURER = "lecturer"     # edytuje własne sylabusy
    STUDENT = "student"       # tylko odczyt


class AuthProvider(str, Enum):
    LOCAL = "local"           # login + hasło
    SSO = "sso"               # konto uczelniane (OAuth2/SAML)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Rola w systemie
    role: Mapped[UserRole] = mapped_column(
        String(50), nullable=False, default=UserRole.LECTURER
    )

    # Auth provider – local lub SSO (konto uczelniane)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        String(50), nullable=False, default=AuthProvider.LOCAL
    )
    sso_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Powiązanie z jednostką akademicką
    academic_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id"), nullable=True
    )

    # Relationships
    academic_unit: Mapped["AcademicUnit"] = relationship(back_populates="users")
    syllabi: Mapped[list["Syllabus"]] = relationship(back_populates="author")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"


class AcademicUnit(Base):
    """Jednostka akademicka – wydział, instytut, katedra."""
    __tablename__ = "academic_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id"), nullable=True
    )

    # Relationships
    parent: Mapped["AcademicUnit | None"] = relationship(
        "AcademicUnit", remote_side="AcademicUnit.id", back_populates="children"
    )
    children: Mapped[list["AcademicUnit"]] = relationship(
        "AcademicUnit", back_populates="parent"
    )
    users: Mapped[list[User]] = relationship(back_populates="academic_unit")
    syllabi: Mapped[list["Syllabus"]] = relationship(back_populates="academic_unit")

    def __repr__(self) -> str:
        return f"<AcademicUnit {self.code}: {self.name}>"
