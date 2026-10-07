"""Celery Beat schedules configuration."""

from app.workers.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "ping-every-minute": {
        "task": "ping",
        "schedule": 60.0,
    },
    "run-drift-check-weekly": {
        "task": "app.workers.tasks.training.run_drift_check_task",
        "schedule": 604800.0,  # Weekly (7 days)
        "args": [30],  # lookback_days=30
    },
}
