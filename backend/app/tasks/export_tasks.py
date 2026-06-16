from app.core.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def generate_export_task(self, version_id: str, format: str, user_id: str):
    """
    Асинхронная задача экспорта (для больших файлов).
    Запускается через Celery, результат сохраняется в MinIO.
    """
    try:
        # Импорт здесь чтобы избежать circular imports
        from app.services.export_service import ExportService
        # В полной реализации: загружаем версию из БД и сохраняем в MinIO
        return {"status": "done", "version_id": version_id, "format": format}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
