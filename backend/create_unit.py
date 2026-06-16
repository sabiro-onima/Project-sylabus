import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import AcademicUnit
async def create():
    async with AsyncSessionLocal() as db:
        unit = AcademicUnit(name="Instytut Technologii Informatycznych", code="ITI")
        db.add(unit)
        await db.commit()
        print("OK:", unit.id)
asyncio.run(create())
