from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.task import Task, TaskCreate
from app.models.user import User

router = APIRouter(tags=["tasks"])

@router.post("/tasks", response_model=Task)
async def create_task(
    task: TaskCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    db_task = Task.model_validate(task)
    db_task.user_id = current_user.id
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@router.get("/tasks", response_model=List[Task])
async def get_tasks(
    skip: int = 0,
    limit: int = 10,
    completed: Optional[bool] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Task).where(Task.user_id == current_user.id)
    if completed is not None:
        query = query.where(Task.completed == completed)
    tasks = session.exec(query.offset(skip).limit(limit)).all()
    return tasks


@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    task = session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="task pas trouve")
    return task


@router.put("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task: TaskCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    old_task = session.get(Task, task_id)
    if not old_task or old_task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="task pas trouve")

    old_task.title = task.title
    old_task.description = task.description
    old_task.created_at = task.created_at
    old_task.completed = task.completed

    session.add(old_task)
    session.commit()
    session.refresh(old_task)
    return old_task


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    task = session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="task pas trouve")

    session.delete(task)
    session.commit()
    return {"message": "task deleted"}


