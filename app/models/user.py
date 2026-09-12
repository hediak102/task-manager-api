from typing import Optional
from sqlmodel import SQLModel, Field

class UserCreate(SQLModel):
    username: str
    email: str
    password: str

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)

class UserRead(SQLModel):
    id: int
    username: str
    is_admin: bool