"""
Интеграционные тесты: auth + syllabi + admin + workflow.

База: PostgreSQL (sylabus_test) — создаётся автоматически.
Изоляция: TRUNCATE всех таблиц перед каждым тестом.

Запуск:
    docker compose run --rm backend python -m pytest tests/test_api_full.py -v
"""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.user import AuthProvider, User, UserRole

# ─── БАЗА ДАННЫХ ──────────────────────────────────────────────────────────────

_PROD_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://sylabus_user:sylabus_pass@postgres:5432/sylabus_db",
)
_BASE = _PROD_URL.rsplit("/", 1)[0]   # все до последнего "/"
TEST_DB_URL = f"{_BASE}/sylabus_test"

# Движок для тестов — создаётся один раз
_test_engine = create_async_engine(TEST_DB_URL, echo=False, pool_pre_ping=True)
_TestSession = async_sessionmaker(
    bind=_test_engine, class_=AsyncSession, expire_on_commit=False
)


# Переопределяем зависимость FastAPI
async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


UNIT_ID = "00000000-0000-0000-0000-000000000001"


# ─── SESSION-ФИКСТУРА: создаём БД и таблицы один раз ────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _init_test_db():
    # 1) Создаём БД sylabus_test если её нет
    admin_engine = create_async_engine(
        _PROD_URL, echo=False, isolation_level="AUTOCOMMIT"
    )
    async with admin_engine.connect() as conn:
        row = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'sylabus_test'")
        )
        if not row.scalar():
            await conn.execute(text("CREATE DATABASE sylabus_test"))
    await admin_engine.dispose()

    # 2) Создаём все таблицы
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 3) Дропаем таблицы после всех тестов
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # 4) Закрываем пул соединений — важно делать ДО закрытия event loop,
    #    чтобы asyncpg успел корректно завершить все соединения.
    await _test_engine.dispose(close=True)
    # Небольшая пауза даёт asyncpg обработать отложенные задачи
    import asyncio as _asyncio
    await _asyncio.sleep(0.1)


# ─── TEST-ФИКСТУРА: TRUNCATE перед каждым тестом ────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Очищаем таблицы быстрым TRUNCATE (без пересоздания схемы)."""
    async with _test_engine.begin() as conn:
        # RESTART IDENTITY сбрасывает sequences; CASCADE чистит FK-зависимости
        await conn.execute(
            text(
                "TRUNCATE TABLE "
                "audit_logs, syllabus_changes, syllabus_program_links, "
                "syllabus_versions, syllabi, study_programs, "
                "users, academic_units "
                "RESTART IDENTITY CASCADE"
            )
        )
        # Вставляем тестовую академическую единицу — нужна для FK в syllabi
        await conn.execute(
            text(
                "INSERT INTO academic_units (id, name, code) "
                "VALUES (:id, 'Wydział Testowy', 'TEST') "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": UNIT_ID},
        )
    yield


# ─── HTTP-клиент ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ─────────────────────────────────────────────────

ADMIN_EMAIL      = "admin@test.pl"
COORDINATOR_EMAIL = "coord@test.pl"
DEFAULT_PASSWORD  = "Haslo123"


async def _create_user(role: UserRole, email: str) -> User:
    """Создаёт пользователя с заданной ролью напрямую в БД."""
    async with _TestSession() as session:
        user = User(
            email=email,
            full_name=f"Test {role.value.title()}",
            hashed_password=hash_password(DEFAULT_PASSWORD),
            role=role,
            auth_provider=AuthProvider.LOCAL,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _login(client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


async def _register_login(
    client: AsyncClient,
    email: str = "user@test.pl",
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Jan Kowalski",
) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert r.status_code == 201, f"Register failed: {r.text}"
    return await _login(client, email, password)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _syllabus_payload(
    course_code: str = "INF001",
    ects: float = 5.0,
    hours_lecture: int = 30,
    hours_laboratory: int = 30,
    hours_self_study: int = 65,
    assessment_methods: list | None = None,
    academic_year: str = "2024/2025",
    semester_number: int = 1,
    semester: str = "winter",
) -> dict:
    if assessment_methods is None:
        assessment_methods = [
            {"method": "exam",    "weight": 60, "description": "Egzamin pisemny"},
            {"method": "project", "weight": 40, "description": "Projekt zaliczeniowy"},
        ]
    return {
        "course_code": course_code,
        "academic_unit_id": UNIT_ID,
        "initial_version": {
            "title_pl": f"Przedmiot {course_code}",
            "title_en": "Course EN",
            "course_type": "lecture",
            "semester": semester,
            "semester_number": semester_number,
            "ects_credits": ects,
            "academic_year": academic_year,
            "hours_lecture": hours_lecture,
            "hours_laboratory": hours_laboratory,
            "hours_self_study": hours_self_study,
            "assessment_methods": assessment_methods,
            "learning_outcomes": [
                {"code": "EK1", "description": "Opis efektu", "category": "knowledge"}
            ],
            "bibliography": [
                {"type": "primary", "citation": "Autor — Tytuł", "url": None}
            ],
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════

class TestRegister:
    async def test_success(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "new@test.pl", "full_name": "Anna Nowak", "password": "Haslo123"
        })
        assert r.status_code == 201
        assert r.json()["email"] == "new@test.pl"
        assert r.json()["role"] == "lecturer"
        assert r.json()["is_active"] is True

    async def test_duplicate_email(self, client):
        p = {"email": "dup@test.pl", "full_name": "Xx Yy", "password": "Haslo123"}
        await client.post("/api/v1/auth/register", json=p)
        r = await client.post("/api/v1/auth/register", json=p)
        assert r.status_code == 400

    async def test_password_too_short(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "x@test.pl", "full_name": "Ab Cd", "password": "Ab1"
        })
        assert r.status_code == 422

    async def test_password_no_uppercase(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "x@test.pl", "full_name": "Ab Cd", "password": "haslo123"
        })
        assert r.status_code == 422

    async def test_password_no_digit(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "x@test.pl", "full_name": "Ab Cd", "password": "HasloHaslo"
        })
        assert r.status_code == 422

    async def test_invalid_email(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "full_name": "Ab Cd", "password": "Haslo123"
        })
        assert r.status_code == 422

    async def test_full_name_too_short(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "x@test.pl", "full_name": "X", "password": "Haslo123"
        })
        assert r.status_code == 422


class TestLogin:
    async def test_success(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "login@test.pl", "full_name": "Lo Gin", "password": "Haslo123"
        })
        r = await client.post("/api/v1/auth/login",
                               data={"username": "login@test.pl", "password": "Haslo123"})
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert "refresh_token" in r.json()
        assert r.json()["token_type"] == "bearer"

    async def test_wrong_password(self, client):
        r = await client.post("/api/v1/auth/login",
                               data={"username": "nobody@test.pl", "password": "Wrong123"})
        assert r.status_code == 401

    async def test_unknown_user(self, client):
        r = await client.post("/api/v1/auth/login",
                               data={"username": "ghost@test.pl", "password": "Haslo123"})
        assert r.status_code == 401

    async def test_inactive_user_blocked(self, client):
        await _create_user(UserRole.LECTURER, "inactive@test.pl")
        async with _TestSession() as s:
            from sqlalchemy import select as _sel
            u = (await s.execute(_sel(User).where(User.email == "inactive@test.pl"))).scalar_one()
            u.is_active = False
            await s.commit()
        r = await client.post("/api/v1/auth/login",
                               data={"username": "inactive@test.pl", "password": DEFAULT_PASSWORD})
        assert r.status_code == 403


class TestMe:
    async def test_returns_user(self, client):
        token = await _register_login(client, "me@test.pl")
        r = await client.get("/api/v1/auth/me", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["email"] == "me@test.pl"

    async def test_unauthenticated(self, client):
        assert (await client.get("/api/v1/auth/me")).status_code == 401

    async def test_invalid_token(self, client):
        r = await client.get("/api/v1/auth/me", headers=_auth("bad.token"))
        assert r.status_code == 401


class TestRefreshToken:
    async def test_success(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "ref@test.pl", "full_name": "Re Fresh", "password": "Haslo123"
        })
        tokens = (await client.post("/api/v1/auth/login",
                                     data={"username": "ref@test.pl", "password": "Haslo123"})).json()
        r = await client.post("/api/v1/auth/refresh",
                               json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_bad_token(self, client):
        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert r.status_code == 401

    async def test_access_token_rejected(self, client):
        token = await _register_login(client, "at@test.pl")
        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
#  SYLLABI — CREATE
# ══════════════════════════════════════════════════════════════════════════════

class TestSyllabusCreate:
    async def test_success(self, client):
        token = await _register_login(client)
        r = await client.post("/api/v1/syllabi/",
                               json=_syllabus_payload(), headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["course_code"] == "INF001"

    async def test_unauthenticated(self, client):
        r = await client.post("/api/v1/syllabi/", json=_syllabus_payload())
        assert r.status_code == 401

    async def test_hours_too_few(self, client):
        token = await _register_login(client)
        r = await client.post("/api/v1/syllabi/",
                               json=_syllabus_payload(ects=5.0, hours_lecture=5,
                                                       hours_laboratory=0, hours_self_study=5),
                               headers=_auth(token))
        assert r.status_code == 422

    async def test_hours_too_many(self, client):
        token = await _register_login(client)
        r = await client.post("/api/v1/syllabi/",
                               json=_syllabus_payload(ects=1.0, hours_lecture=200,
                                                       hours_laboratory=0, hours_self_study=200),
                               headers=_auth(token))
        assert r.status_code == 422

    async def test_weights_not_100(self, client):
        token = await _register_login(client)
        r = await client.post("/api/v1/syllabi/",
                               json=_syllabus_payload(assessment_methods=[
                                   {"method": "exam", "weight": 50},
                                   {"method": "project", "weight": 30},
                               ]), headers=_auth(token))
        assert r.status_code == 422

    async def test_bad_year_format(self, client):
        token = await _register_login(client)
        p = _syllabus_payload()
        p["initial_version"]["academic_year"] = "2024-2025"
        r = await client.post("/api/v1/syllabi/", json=p, headers=_auth(token))
        assert r.status_code == 422

    async def test_non_consecutive_year(self, client):
        token = await _register_login(client)
        p = _syllabus_payload()
        p["initial_version"]["academic_year"] = "2024/2026"
        r = await client.post("/api/v1/syllabi/", json=p, headers=_auth(token))
        assert r.status_code == 422

    async def test_semester_out_of_range(self, client):
        token = await _register_login(client)
        r = await client.post("/api/v1/syllabi/",
                               json=_syllabus_payload(semester_number=13),
                               headers=_auth(token))
        assert r.status_code == 422

    async def test_zero_ects(self, client):
        token = await _register_login(client)
        p = _syllabus_payload()
        p["initial_version"]["ects_credits"] = 0
        r = await client.post("/api/v1/syllabi/", json=p, headers=_auth(token))
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  SYLLABI — READ
# ══════════════════════════════════════════════════════════════════════════════

class TestSyllabusRead:
    async def test_list_empty(self, client):
        token = await _register_login(client)
        r = await client.get("/api/v1/syllabi/", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["total"] == 0

    async def test_list_after_create(self, client):
        token = await _register_login(client)
        await client.post("/api/v1/syllabi/", json=_syllabus_payload(), headers=_auth(token))
        r = await client.get("/api/v1/syllabi/", headers=_auth(token))
        assert r.json()["total"] >= 1

    async def test_get_by_id(self, client):
        token = await _register_login(client)
        sid = (await client.post("/api/v1/syllabi/",
                                  json=_syllabus_payload(), headers=_auth(token))).json()["id"]
        r = await client.get(f"/api/v1/syllabi/{sid}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["id"] == sid

    async def test_get_nonexistent(self, client):
        token = await _register_login(client)
        r = await client.get(f"/api/v1/syllabi/{uuid.uuid4()}", headers=_auth(token))
        assert r.status_code == 404

    async def test_unauthenticated(self, client):
        assert (await client.get("/api/v1/syllabi/")).status_code == 401

    async def test_pagination(self, client):
        token = await _register_login(client)
        for i in range(3):
            await client.post("/api/v1/syllabi/",
                               json=_syllabus_payload(course_code=f"PAG{i:03d}"),
                               headers=_auth(token))
        r = await client.get("/api/v1/syllabi/?page=1&size=2", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 2
        assert r.json()["total"] >= 3


# ══════════════════════════════════════════════════════════════════════════════
#  SYLLABI — VERSIONS
# ══════════════════════════════════════════════════════════════════════════════

class TestSyllabusVersions:
    async def test_create_new_version(self, client):
        token = await _register_login(client)
        sid = (await client.post("/api/v1/syllabi/",
                                  json=_syllabus_payload(), headers=_auth(token))).json()["id"]
        v2 = _syllabus_payload(academic_year="2025/2026")["initial_version"]
        r = await client.post(f"/api/v1/syllabi/{sid}/versions", json=v2, headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["version_number"] == 2

    async def test_version_history(self, client):
        token = await _register_login(client)
        sid = (await client.post("/api/v1/syllabi/",
                                  json=_syllabus_payload(), headers=_auth(token))).json()["id"]
        r = await client.get(f"/api/v1/syllabi/{sid}/versions", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_update_draft(self, client):
        token = await _register_login(client)
        data = (await client.post("/api/v1/syllabi/",
                                   json=_syllabus_payload(), headers=_auth(token))).json()
        vid = data["latest_version"]["id"]
        r = await client.patch(f"/api/v1/syllabi/versions/{vid}",
                                json={"title_pl": "Nowy tytuł"},
                                headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["title_pl"] == "Nowy tytuł"

    async def test_update_nonexistent(self, client):
        token = await _register_login(client)
        r = await client.patch(f"/api/v1/syllabi/versions/{uuid.uuid4()}",
                                json={"title_pl": "X"},
                                headers=_auth(token))
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW: DRAFT → PENDING → APPROVED
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflow:
    async def _make(self, client, token, code="WF001"):
        data = (await client.post("/api/v1/syllabi/",
                                   json=_syllabus_payload(course_code=code),
                                   headers=_auth(token))).json()
        return data["id"], data["latest_version"]["id"]

    async def test_submit(self, client):
        token = await _register_login(client, "l1@wf.pl")
        _, vid = await self._make(client, token)
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    async def test_double_submit_rejected(self, client):
        token = await _register_login(client, "l2@wf.pl")
        _, vid = await self._make(client, token, "WF002")
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(token))
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(token))
        assert r.status_code == 422

    async def test_lecturer_cannot_approve(self, client):
        token = await _register_login(client, "l3@wf.pl")
        _, vid = await self._make(client, token, "WF003")
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(token))
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(token))
        assert r.status_code == 403

    async def test_coordinator_approves(self, client):
        await _create_user(UserRole.COORDINATOR, COORDINATOR_EMAIL)
        coord = await _login(client, COORDINATOR_EMAIL)
        lect = await _register_login(client, "l4@wf.pl")
        _, vid = await self._make(client, lect, "WF004")
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(lect))
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(coord))
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    async def test_approve_draft_rejected(self, client):
        await _create_user(UserRole.COORDINATOR, "c2@wf.pl")
        coord = await _login(client, "c2@wf.pl")
        lect = await _register_login(client, "l5@wf.pl")
        _, vid = await self._make(client, lect, "WF005")
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(coord))
        assert r.status_code == 422

    async def test_edit_approved_rejected(self, client):
        await _create_user(UserRole.COORDINATOR, "c3@wf.pl")
        coord = await _login(client, "c3@wf.pl")
        lect = await _register_login(client, "l6@wf.pl")
        _, vid = await self._make(client, lect, "WF006")
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(lect))
        await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(coord))
        r = await client.patch(f"/api/v1/syllabi/versions/{vid}",
                                json={"title_pl": "Zmiana po approve"},
                                headers=_auth(lect))
        assert r.status_code == 422

    async def test_full_happy_path(self, client):
        await _create_user(UserRole.COORDINATOR, "c4@wf.pl")
        coord = await _login(client, "c4@wf.pl")
        lect = await _register_login(client, "l7@wf.pl")
        _, vid = await self._make(client, lect, "WF007")

        r = await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(lect))
        assert r.json()["status"] == "pending"

        r = await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(coord))
        assert r.json()["status"] == "approved"


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN
# ══════════════════════════════════════════════════════════════════════════════

class TestAdmin:
    async def test_lecturer_blocked(self, client):
        token = await _register_login(client, "l@adm.pl")
        r = await client.get("/api/v1/admin/users", headers=_auth(token))
        assert r.status_code == 403

    async def test_list_users(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        r = await client.get("/api/v1/admin/users", headers=_auth(token))
        assert r.status_code == 200
        assert "items" in r.json() and "total" in r.json()

    async def test_stats(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        r = await client.get("/api/v1/admin/stats", headers=_auth(token))
        assert r.status_code == 200
        assert {"total_users", "total_syllabi", "role_counts"} <= r.json().keys()

    async def test_update_role(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        target = await _create_user(UserRole.LECTURER, "tgt@adm.pl")
        r = await client.patch(f"/api/v1/admin/users/{target.id}",
                                json={"role": "coordinator"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["role"] == "coordinator"

    async def test_cannot_demote_self(self, client):
        admin = await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        r = await client.patch(f"/api/v1/admin/users/{admin.id}",
                                json={"role": "lecturer"}, headers=_auth(token))
        assert r.status_code == 400

    async def test_deactivate(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        target = await _create_user(UserRole.LECTURER, "deact@adm.pl")
        r = await client.patch(f"/api/v1/admin/users/{target.id}",
                                json={"is_active": False}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    async def test_update_nonexistent(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        r = await client.patch(f"/api/v1/admin/users/{uuid.uuid4()}",
                                json={"role": "coordinator"}, headers=_auth(token))
        assert r.status_code == 404

    async def test_invalid_role(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        target = await _create_user(UserRole.LECTURER, "r2@adm.pl")
        r = await client.patch(f"/api/v1/admin/users/{target.id}",
                                json={"role": "superuser"}, headers=_auth(token))
        assert r.status_code == 400

    async def test_search(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        await _create_user(UserRole.LECTURER, "findme@adm.pl")
        r = await client.get("/api/v1/admin/users?search=findme", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    async def test_filter_by_role(self, client):
        await _create_user(UserRole.ADMIN, ADMIN_EMAIL)
        token = await _login(client, ADMIN_EMAIL)
        r = await client.get("/api/v1/admin/users?role=admin", headers=_auth(token))
        assert r.status_code == 200
        for u in r.json()["items"]:
            assert u["role"] == "admin"


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════

class TestHealth:
    async def test_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ══════════════════════════════════════════════════════════════════════════════
#  UNIT TESTS — Pydantic schemas (без HTTP)
# ══════════════════════════════════════════════════════════════════════════════

class TestRegisterSchema:
    def test_valid(self):
        from app.schemas.auth import RegisterRequest
        r = RegisterRequest(email="a@b.pl", full_name="Jan Kowalski", password="Haslo123")
        assert r.email == "a@b.pl"

    def test_no_uppercase(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.pl", full_name="AB CD", password="haslo123")

    def test_no_digit(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.pl", full_name="AB CD", password="HasloHaslo")


class TestSyllabusSchema:
    def _base(self):
        return {
            "title_pl": "Matematyka",
            "course_type": "lecture",
            "semester": "winter",
            "semester_number": 2,
            "ects_credits": 4.0,
            "academic_year": "2024/2025",
            "hours_lecture": 30,
            "hours_self_study": 70,
            "assessment_methods": [{"method": "exam", "weight": 100}],
        }

    def test_valid(self):
        from app.schemas.syllabus import SyllabusVersionCreate
        obj = SyllabusVersionCreate(**self._base())
        assert obj.ects_credits == 4.0

    def test_weights_not_100(self):
        from pydantic import ValidationError
        from app.schemas.syllabus import SyllabusVersionCreate
        d = {**self._base(), "assessment_methods": [
            {"method": "exam", "weight": 40},
            {"method": "quiz", "weight": 40},
        ]}
        with pytest.raises(ValidationError):
            SyllabusVersionCreate(**d)

    def test_hours_mismatch(self):
        from pydantic import ValidationError
        from app.schemas.syllabus import SyllabusVersionCreate
        d = {**self._base(), "ects_credits": 10.0,
             "hours_lecture": 10, "hours_self_study": 10}
        with pytest.raises(ValidationError):
            SyllabusVersionCreate(**d)

    def test_non_consecutive_year(self):
        from pydantic import ValidationError
        from app.schemas.syllabus import SyllabusVersionCreate
        with pytest.raises(ValidationError):
            SyllabusVersionCreate(**{**self._base(), "academic_year": "2024/2026"})


# ══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW: REJECT
# ══════════════════════════════════════════════════════════════════════════════

class TestReject:
    async def _make_pending(self, client, lect_email="rej_l@wf.pl", code="REJ001"):
        lect = await _register_login(client, lect_email)
        data = (await client.post("/api/v1/syllabi/",
                                   json=_syllabus_payload(course_code=code),
                                   headers=_auth(lect))).json()
        vid = data["latest_version"]["id"]
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(lect))
        return lect, vid

    async def test_coordinator_rejects(self, client):
        await _create_user(UserRole.COORDINATOR, "c_rej@wf.pl")
        coord = await _login(client, "c_rej@wf.pl")
        _, vid = await self._make_pending(client)
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/reject",
                               json={"reason": "Brakuje efektów kształcenia"},
                               headers=_auth(coord))
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    async def test_lecturer_cannot_reject(self, client):
        lect, vid = await self._make_pending(client, "rej_l2@wf.pl", "REJ002")
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/reject",
                               json={}, headers=_auth(lect))
        assert r.status_code == 403

    async def test_reject_draft_fails(self, client):
        await _create_user(UserRole.COORDINATOR, "c_rej2@wf.pl")
        coord = await _login(client, "c_rej2@wf.pl")
        lect = await _register_login(client, "rej_l3@wf.pl")
        data = (await client.post("/api/v1/syllabi/",
                                   json=_syllabus_payload(course_code="REJ003"),
                                   headers=_auth(lect))).json()
        vid = data["latest_version"]["id"]
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/reject",
                               json={}, headers=_auth(coord))
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW: ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════

class TestArchive:
    async def test_coordinator_archives_approved(self, client):
        await _create_user(UserRole.COORDINATOR, "c_arch@wf.pl")
        coord = await _login(client, "c_arch@wf.pl")
        lect = await _register_login(client, "arch_l@wf.pl")
        data = (await client.post("/api/v1/syllabi/",
                                   json=_syllabus_payload(course_code="ARCH001"),
                                   headers=_auth(lect))).json()
        vid = data["latest_version"]["id"]
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(lect))
        await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(coord))
        r = await client.post(f"/api/v1/syllabi/versions/{vid}/archive", headers=_auth(coord))
        assert r.status_code == 200
        assert r.json()["status"] == "archived"


# ══════════════════════════════════════════════════════════════════════════════
#  FILTER: course_type
# ══════════════════════════════════════════════════════════════════════════════

class TestFilterCourseType:
    async def test_filter_by_course_type(self, client):
        token = await _register_login(client, "ft@test.pl")
        await client.post("/api/v1/syllabi/",
                           json=_syllabus_payload(course_code="FT001"),
                           headers=_auth(token))
        r = await client.get("/api/v1/syllabi/?course_type=lecture", headers=_auth(token))
        assert r.status_code == 200
        for item in r.json()["items"]:
            # każda wersja musi być lecture
            assert item["latest_version"]["course_type"] == "lecture"


# ══════════════════════════════════════════════════════════════════════════════
#  SUBJECT GRID
# ══════════════════════════════════════════════════════════════════════════════

class TestSubjectGrid:
    async def test_grid_empty(self, client):
        token = await _register_login(client, "grid@test.pl")
        r = await client.get(
            f"/api/v1/syllabi/grid?academic_unit_id={UNIT_ID}&academic_year=2024/2025",
            headers=_auth(token)
        )
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    async def test_grid_shows_approved_only(self, client):
        await _create_user(UserRole.COORDINATOR, "grid_coord@test.pl")
        coord = await _login(client, "grid_coord@test.pl")
        lect = await _register_login(client, "grid_lect@test.pl")

        # Utwórz i zatwierdź sylabus
        data = (await client.post("/api/v1/syllabi/",
                                   json=_syllabus_payload(course_code="GRID001"),
                                   headers=_auth(lect))).json()
        vid = data["latest_version"]["id"]
        await client.post(f"/api/v1/syllabi/versions/{vid}/submit", headers=_auth(lect))
        await client.post(f"/api/v1/syllabi/versions/{vid}/approve", headers=_auth(coord))

        r = await client.get(
            f"/api/v1/syllabi/grid?academic_unit_id={UNIT_ID}&academic_year=2024/2025",
            headers=_auth(lect)
        )
        assert r.status_code == 200
        grid = r.json()
        # Semestr 1 powinien zawierać GRID001
        assert "1" in grid
        codes = [s["course_code"] for s in grid["1"]]
        assert "GRID001" in codes

    async def test_grid_bad_year_format(self, client):
        token = await _register_login(client, "grid2@test.pl")
        r = await client.get(
            f"/api/v1/syllabi/grid?academic_unit_id={UNIT_ID}&academic_year=2024-2025",
            headers=_auth(token)
        )
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  STUDY PROGRAMS
# ══════════════════════════════════════════════════════════════════════════════

class TestStudyPrograms:
    def _payload(self, code="INF-LIC"):
        return {
            "name": "Informatyka I stopień",
            "code": code,
            "degree": "bachelor",
            "form": "full-time",
            "duration_semesters": 7,
            "academic_unit_id": UNIT_ID,
        }

    async def test_create(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c@test.pl")
        coord = await _login(client, "prog_c@test.pl")
        r = await client.post("/api/v1/programs/", json=self._payload(), headers=_auth(coord))
        assert r.status_code == 201
        assert r.json()["code"] == "INF-LIC"

    async def test_list(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c2@test.pl")
        coord = await _login(client, "prog_c2@test.pl")
        await client.post("/api/v1/programs/", json=self._payload("INF-LIC2"), headers=_auth(coord))
        r = await client.get("/api/v1/programs/", headers=_auth(coord))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_duplicate_code(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c3@test.pl")
        coord = await _login(client, "prog_c3@test.pl")
        await client.post("/api/v1/programs/", json=self._payload("DUP"), headers=_auth(coord))
        r = await client.post("/api/v1/programs/", json=self._payload("DUP"), headers=_auth(coord))
        assert r.status_code == 400

    async def test_get_by_id(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c4@test.pl")
        coord = await _login(client, "prog_c4@test.pl")
        pid = (await client.post("/api/v1/programs/",
                                  json=self._payload("INF-LIC4"),
                                  headers=_auth(coord))).json()["id"]
        r = await client.get(f"/api/v1/programs/{pid}", headers=_auth(coord))
        assert r.status_code == 200
        assert r.json()["id"] == pid

    async def test_update(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c5@test.pl")
        coord = await _login(client, "prog_c5@test.pl")
        pid = (await client.post("/api/v1/programs/",
                                  json=self._payload("INF-LIC5"),
                                  headers=_auth(coord))).json()["id"]
        r = await client.patch(f"/api/v1/programs/{pid}",
                                json={"name": "Zmieniona nazwa"},
                                headers=_auth(coord))
        assert r.status_code == 200
        assert r.json()["name"] == "Zmieniona nazwa"

    async def test_lecturer_cannot_create(self, client):
        lect = await _register_login(client, "prog_l@test.pl")
        r = await client.post("/api/v1/programs/", json=self._payload("NOPE"),
                               headers=_auth(lect))
        assert r.status_code == 403

    async def test_link_syllabus(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c6@test.pl")
        coord = await _login(client, "prog_c6@test.pl")
        lect = await _register_login(client, "prog_l2@test.pl")

        pid = (await client.post("/api/v1/programs/",
                                  json=self._payload("INF-LIC6"),
                                  headers=_auth(coord))).json()["id"]
        sid = (await client.post("/api/v1/syllabi/",
                                  json=_syllabus_payload(course_code="PROG001"),
                                  headers=_auth(lect))).json()["id"]

        r = await client.post(f"/api/v1/programs/{pid}/syllabi/{sid}",
                               json={"semester_number": 1},
                               headers=_auth(coord))
        assert r.status_code == 201

        r = await client.get(f"/api/v1/programs/{pid}/syllabi", headers=_auth(coord))
        assert r.status_code == 200
        codes = [x["course_code"] for x in r.json()]
        assert "PROG001" in codes

    async def test_unlink_syllabus(self, client):
        await _create_user(UserRole.COORDINATOR, "prog_c7@test.pl")
        coord = await _login(client, "prog_c7@test.pl")
        lect = await _register_login(client, "prog_l3@test.pl")

        pid = (await client.post("/api/v1/programs/",
                                  json=self._payload("INF-LIC7"),
                                  headers=_auth(coord))).json()["id"]
        sid = (await client.post("/api/v1/syllabi/",
                                  json=_syllabus_payload(course_code="PROG002"),
                                  headers=_auth(lect))).json()["id"]

        await client.post(f"/api/v1/programs/{pid}/syllabi/{sid}",
                           json={"semester_number": 2},
                           headers=_auth(coord))
        r = await client.delete(f"/api/v1/programs/{pid}/syllabi/{sid}",
                                 headers=_auth(coord))
        assert r.status_code == 204
