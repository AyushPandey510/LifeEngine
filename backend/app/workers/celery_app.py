"""
Celery Application
Background task worker for Life Engine AI
"""
from importlib import import_module

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "lifeengine",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
}

try:
    daily_tasks = import_module("app.workers.daily_tasks")
except ModuleNotFoundError:
    daily_tasks = None

if daily_tasks is not None:
    celery_app.conf.beat_schedule.update(
        getattr(daily_tasks, "BEAT_SCHEDULE", {})
    )
