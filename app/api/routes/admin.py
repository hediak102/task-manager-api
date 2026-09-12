from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.api.deps import get_current_user
from app.models.task import Task
from app.models.user import User,UserRead
from app.api.deps import get_current_admin

router=APIRouter(tags=["admin"])

@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/admin/users", response_model=List[UserRead])
async def get_all_users(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    users = session.exec(select(User)).all()
    return users

@router.get("/admin/tasks", response_model=List[Task])
async def get_all_tasks(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    tasks = session.exec(select(Task)).all()
    return tasks