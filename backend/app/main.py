from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.endpoints import auth, syllabi, export, admin, programs, units
from app.core.config import settings
from app.core.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Tworzenie tabel (w produkcji użyj Alembic zamiast tego)
    if settings.APP_ENV != "production":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


# ─── SENTRY (error tracking) ─────────────────────────────────────────────────
if settings.APP_ENV == "production":
    sentry_sdk.init(
        dsn="",   # uzupełnij DSN z dashboardu Sentry
        traces_sample_rate=0.2,
    )


# ─── APP ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="System zarządzania sylabusami dla uczelni wyższej",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── PROMETHEUS metrics ──────────────────────────────────────────────────────
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics")

# ─── ROUTERS ─────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(syllabi.router, prefix=settings.API_V1_STR)
app.include_router(export.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(programs.router, prefix=settings.API_V1_STR)
app.include_router(units.router, prefix=settings.API_V1_STR)


# ─── HEALTH CHECK ────────────────────────────────────────────────────────────
@app.get("/health", tags=["monitoring"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}
