"""
Endpointy auth:
  POST /auth/register   – rejestracja (login + hasło)
  POST /auth/login      – logowanie (OAuth2PasswordRequestForm)
  POST /auth/refresh    – odświeżenie access tokenu
  GET  /auth/sso/login  – redirect do uczelnianego SSO
  GET  /auth/sso/callback – callback z SSO
  GET  /auth/me         – dane zalogowanego użytkownika
"""
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import AuthProvider, User, UserRole
from app.schemas.auth import (
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── REJESTRACJA ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Sprawdzenie czy email już istnieje
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email już jest zarejestrowany.")

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=UserRole.LECTURER,
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(user)
    await db.flush()
    return UserResponse.model_validate(user)


# ─── LOGOWANIE (login + hasło) ───────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto jest nieaktywne.")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


# ─── REFRESH TOKEN ───────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Nieprawidłowy typ tokenu.")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje.")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


# ─── SSO (konto uczelniane) ──────────────────────────────────────────────────

@router.get("/sso/login")
async def sso_login():
    """Przekierowanie do uczelnianego IdP (OAuth2 Authorization Code)."""
    if not settings.SSO_ENABLED:
        raise HTTPException(status_code=404, detail="SSO nie jest włączone.")

    params = urlencode({
        "response_type": "code",
        "client_id": settings.SSO_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/api/v1/auth/sso/callback",
        "scope": "openid email profile",
    })
    return {"redirect_url": f"{settings.SSO_AUTHORIZATION_URL}?{params}"}


@router.get("/sso/callback")
async def sso_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Callback z uczelnianego IdP – wymienia code na token i loguje użytkownika."""
    if not settings.SSO_ENABLED:
        raise HTTPException(status_code=404, detail="SSO nie jest włączone.")

    async with httpx.AsyncClient() as client:
        # 1. Wymiana code → token
        token_resp = await client.post(
            settings.SSO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.SSO_CLIENT_ID,
                "client_secret": settings.SSO_CLIENT_SECRET,
                "redirect_uri": "http://localhost:8000/api/v1/auth/sso/callback",
            },
        )
        token_resp.raise_for_status()
        sso_token = token_resp.json()["access_token"]

        # 2. Pobranie danych użytkownika z IdP
        userinfo_resp = await client.get(
            settings.SSO_USERINFO_URL,
            headers={"Authorization": f"Bearer {sso_token}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    sso_subject = userinfo.get("sub")
    email = userinfo.get("email")
    full_name = userinfo.get("name", email)

    # 3. Znajdź lub utwórz użytkownika
    result = await db.execute(select(User).where(User.sso_subject == sso_subject))
    user = result.scalar_one_or_none()

    if not user:
        # Sprawdź czy ktoś już ma ten email (rejestrował się lokalnie)
        result2 = await db.execute(select(User).where(User.email == email))
        user = result2.scalar_one_or_none()

        if user:
            # Połącz konto lokalne z SSO
            user.sso_subject = sso_subject
            user.auth_provider = AuthProvider.SSO
        else:
            # Nowy użytkownik z SSO
            user = User(
                email=email,
                full_name=full_name,
                sso_subject=sso_subject,
                auth_provider=AuthProvider.SSO,
                role=UserRole.LECTURER,
            )
            db.add(user)
            await db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


# ─── ME ──────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
