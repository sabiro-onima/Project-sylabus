"""
Endpointy eksportu:
  GET /export/{version_id}/pdf   – pobierz PDF
  GET /export/{version_id}/docx  – pobierz DOCX
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.syllabus import Syllabus, SyllabusVersion
from app.models.user import User
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


async def _get_version(version_id: uuid.UUID, db: AsyncSession) -> tuple[SyllabusVersion, str]:
    result = await db.execute(
        select(SyllabusVersion, Syllabus.course_code)
        .join(Syllabus, Syllabus.id == SyllabusVersion.syllabus_id)
        .where(SyllabusVersion.id == version_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Wersja syllabusa nie istnieje.")
    return row[0], row[1]


@router.get("/{version_id}/pdf")
async def export_pdf(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    version, course_code = await _get_version(version_id, db)
    svc = ExportService()
    pdf_bytes = svc.generate_pdf(version, course_code)

    filename = f"sylabus_{course_code}_{version.academic_year.replace('/', '-')}_v{version.version_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{version_id}/docx")
async def export_docx(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    version, course_code = await _get_version(version_id, db)
    svc = ExportService()
    docx_bytes = svc.generate_docx(version, course_code)

    filename = f"sylabus_{course_code}_{version.academic_year.replace('/', '-')}_v{version.version_number}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
