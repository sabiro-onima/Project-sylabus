#!/usr/bin/env python3
"""
Script to create an admin user.
Usage: python create_admin.py --email admin@example.com --name "Admin User" --password SecurePass1
"""
import asyncio
import argparse

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, AuthProvider


async def create_admin(email: str, full_name: str, password: str):
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                await db.commit()
                print(f"✅ User '{email}' promoted to ADMIN.")
            else:
                print(f"ℹ️  User '{email}' is already an ADMIN.")
            return

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            auth_provider=AuthProvider.LOCAL,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Admin user '{email}' created successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(create_admin(args.email, args.name, args.password))
