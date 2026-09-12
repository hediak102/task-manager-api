from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class TaskCreate(SQLModel):
    title: str = Field(min_length=1)
    description: str
    completed: bool = False
    created_at: datetime
    due_date: Optional[datetime] = None

class Task(TaskCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    reminder_sent: bool = Field(default=False)
    overdue_notified: bool = Field(default=False)