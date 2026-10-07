"""Celery worker application configuration and scheduled tasks."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "agriscope_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.workers.tasks.training.*": {"queue": "training"},
        "app.workers.tasks.*": {"queue": "default"},
    },
)


@celery_app.task(name="ping")
def ping_task() -> str:
    """Trivial ping task verifying worker connectivity."""
    return "pong"
