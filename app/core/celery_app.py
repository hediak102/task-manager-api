from celery import Celery
from celery.schedules import crontab
from app.core.config import REDIS_URL

celery_app = Celery(
    "task_manager",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.reminders"],
)

celery_app.conf.timezone = "Europe/Paris"

celery_app.conf.beat_schedule = {
    "check-due-tasks-hourly": {
        "task": "app.tasks.reminders.check_due_tasks",
        "schedule": crontab(minute=0),  # toutes les heures pile
    },
    "check-overdue-tasks-daily": {
        "task": "app.tasks.reminders.check_overdue_tasks",
        "schedule": crontab(hour=8, minute=0),  # tous les jours à 8h
    },
}