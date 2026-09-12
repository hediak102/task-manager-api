from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.core.celery_app import celery_app
from app.db.session import engine
from app.models.task import Task
from app.models.user import User
from app.tasks.email import send_email


@celery_app.task
def check_due_tasks():
    now = datetime.utcnow()
    window_end = now + timedelta(hours=1)

    with Session(engine) as session:
        query = select(Task).where(
            Task.completed == False,
            Task.reminder_sent == False,
            Task.due_date != None,
            Task.due_date <= window_end,
            Task.due_date >= now,
        )
        tasks = session.exec(query).all()

        for task in tasks:
            user = session.get(User, task.user_id)
            if not user:
                continue
            send_email(
                to=user.email,
                subject=f"Rappel : « {task.title} » arrive à échéance",
                body=f"Ta tâche « {task.title} » est due le {task.due_date}.",
            )
            task.reminder_sent = True
            session.add(task)

        session.commit()


@celery_app.task
def check_overdue_tasks():
    now = datetime.utcnow()

    with Session(engine) as session:
        query = select(Task).where(
            Task.completed == False,
            Task.overdue_notified == False,
            Task.due_date != None,
            Task.due_date < now,
        )
        tasks = session.exec(query).all()

        for task in tasks:
            user = session.get(User, task.user_id)
            if not user:
                continue
            send_email(
                to=user.email,
                subject=f"⚠️ Tâche en retard : « {task.title} »",
                body=f"Ta tâche « {task.title} » était due le {task.due_date} et n'est pas terminée.",
            )
            task.overdue_notified = True
            session.add(task)

        session.commit()