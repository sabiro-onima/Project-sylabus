"""
Testy integracyjne: auth + syllabus API.
Używają bazy in-memory (SQLite async) i testowego klienta FastAPI.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import get_db
from app.models import Base

# ─── TEST DATABASE ────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── HELPERS ─────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email="test@uczelnia.pl", password="Haslo123") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Jan Kowalski",
        "password": password,
    })
    resp = await client.post("/api/v1/auth/login", data={
        "username": email,
        "password": password,
    })
    return resp.json()["access_token"]


# ─── AUTH TESTS ───────────────────────────────────────────────────────────────

class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "user@test.pl",
            "full_name": "Anna Nowak",
            "password": "Haslo123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "user@test.pl"
        assert data["role"] == "lecturer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@test.pl", "full_name": "X", "password": "Haslo123"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "x@test.pl", "full_name": "X", "password": "short"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_no_uppercase(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "x@test.pl", "full_name": "X", "password": "haslo123"
        })
        assert resp.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "login@test.pl", "full_name": "X", "password": "Haslo123"
        })
        resp = await client.post("/api/v1/auth/login", data={
            "username": "login@test.pl", "password": "Haslo123"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert "refresh_token" in resp.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", data={
            "username": "noone@test.pl", "password": "Wrong123"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint(self, client: AsyncClient):
        token = await register_and_login(client)
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@uczelnia.pl"


# ─── SYLLABUS TESTS ───────────────────────────────────────────────────────────

VALID_SYLLABUS_PAYLOAD = {
    "course_code": "INF001",
    "academic_unit_id": "00000000-0000-0000-0000-000000000001",
    "initial_version": {
        "title_pl": "Algorytmy i struktury danych",
        "title_en": "Algorithms and Data Structures",
        "course_type": "lecture",
        "semester": "winter",
        "semester_number": 1,
        "ects_credits": 5.0,
        "academic_year": "2024/2025",
        "hours_lecture": 30,
        "hours_laboratory": 30,
        "hours_self_study": 65,
        "assessment_methods": [
            {"method": "exam", "weight": 60, "description": "Egzamin pisemny"},
            {"method": "project", "weight": 40, "description": "Projekt zaliczeniowy"},
        ],
        "learning_outcomes": [
            {"code": "EK1", "description": "Zna podstawowe struktury danych", "category": "knowledge"},
        ],
        "bibliography": [
            {"type": "primary", "citation": "Cormen T.H. — Wprowadzenie do algorytmów", "url": None},
        ],
    }
}


class TestSyllabus:
    @pytest.mark.asyncio
    async def test_create_syllabus(self, client: AsyncClient):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/v1/syllabi/",
            json=VALID_SYLLABUS_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["course_code"] == "INF001"

    @pytest.mark.asyncio
    async def test_list_syllabi(self, client: AsyncClient):
        token = await register_and_login(client)
        await client.post(
            "/api/v1/syllabi/",
            json=VALID_SYLLABUS_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/api/v1/syllabi/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_invalid_ects_hours(self, client: AsyncClient):
        """Walidacja: godziny nie pasują do ECTS."""
        token = await register_and_login(client)
        bad_payload = VALID_SYLLABUS_PAYLOAD.copy()
        bad_payload["initial_version"] = {
            **VALID_SYLLABUS_PAYLOAD["initial_version"],
            "ects_credits": 5.0,
            "hours_lecture": 5,      # zbyt mało godzin dla 5 ECTS
            "hours_self_study": 5,
        }
        resp = await client.post(
            "/api/v1/syllabi/",
            json=bad_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_assessment_weights(self, client: AsyncClient):
        """Walidacja: suma wag != 100%."""
        token = await register_and_login(client)
        bad_payload = VALID_SYLLABUS_PAYLOAD.copy()
        bad_payload["initial_version"] = {
            **VALID_SYLLABUS_PAYLOAD["initial_version"],
            "assessment_methods": [
                {"method": "exam", "weight": 50},
                {"method": "project", "weight": 30},   # suma = 80, nie 100
            ],
        }
        resp = await client.post(
            "/api/v1/syllabi/",
            json=bad_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated_access(self, client: AsyncClient):
        resp = await client.get("/api/v1/syllabi/")
        assert resp.status_code == 401
