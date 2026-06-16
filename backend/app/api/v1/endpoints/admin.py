"""
Admin API endpoints – only accessible to users with ADMIN role.
  GET  /admin/users          – list users with optional search/role filter
  PATCH /admin/users/{id}    – update user role and/or active status
  GET  /admin/stats          – system statistics
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.models.syllabus import Syllabus
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UsersListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int


# ─── LIST USERS ──────────────────────────────────────────────────────────────

@router.get("/users", response_model=UsersListResponse)
async def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = select(User)

    if search:
        like = f"%{search}%"
        query = query.where(
            (User.full_name.ilike(like)) | (User.email.ilike(like))
        )
    if role:
        query = query.where(User.role == role)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * size).limit(size).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return UsersListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
    )


# ─── UPDATE USER ─────────────────────────────────────────────────────────────

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje.")

    # Prevent admin from revoking their own admin role
    if str(user.id) == str(admin.id) and body.role and body.role != "admin":
        raise HTTPException(status_code=400, detail="Nie możesz zmienić własnej roli admina.")

    if body.role is not None:
        if body.role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=400, detail=f"Nieprawidłowa rola: {body.role}")
        user.role = body.role

    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    return UserResponse.model_validate(user)


# ─── STATS ───────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar_one()
    admin_users = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.ADMIN))).scalar_one()
    total_syllabi = (await db.execute(select(func.count(Syllabus.id)))).scalar_one()

    role_counts = {}
    for role in UserRole:
        count = (await db.execute(
            select(func.count(User.id)).where(User.role == role)
        )).scalar_one()
        role_counts[role.value] = count

    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "total_syllabi": total_syllabi,
        "role_counts": role_counts,
    }
