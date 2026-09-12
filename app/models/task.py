from typing import Optional
from sqlmodel import SQLModel, Field

class TaskCreate(SQLModel):
    title: str = Field(min_length=1)
    description: str
    completed: bool = False
    created_at: str

class Task(TaskCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")