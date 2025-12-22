from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rebug",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.analysis", "app.tasks.impact"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "impact-scan-every-15-minutes": {
            "task": "impact.scan_impact_links",
            "schedule": 15 * 60,
        },
    },
)
