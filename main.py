from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Field, Session, SQLModel, create_engine, select
from passlib.context import CryptContext
from jose import jwt, JWTError
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()


# DATABASE SETUP

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session



# MODELS


class TaskCreate(SQLModel):
    title: str = Field(min_length=1)
    description: str
    completed: bool = False
    created_at: str

class Task(TaskCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")


class UserCreate(SQLModel):
    username: str
    password: str

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
class RefreshRequest(BaseModel):
    refresh_token: str
class UserRead(SQLModel):
    id: int
    username: str
    is_admin: bool


# AUTH UTILITIES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set — check your .env file")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user
def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="admin access required")
    return current_user


# APP SETUP

app = FastAPI()

origins = [
    "http://localhost:5173",   #React en dev
    "https://task-manager-frontend-0zrd.onrender.com",
    "http://localhost:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#@app.on_event("startup")
#def on_startup():
    #create_db_and_tables()

@app.get("/")
async def read_root():
    return {"message": "api is running"}



# AUTH ROUTES


@app.post("/register")
async def register(user: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="username already taken")

    new_user = User(username=user.username, hashed_password=hash_password(user.password))
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "user created", "username": new_user.username}


@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="incorrect username or password")

    token = create_access_token({"sub": user.username})
    refresh_token = create_refresh_token({"sub": user.username})
    return {"access_token": token,"refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/refresh")
async def refresh_access_token(body: RefreshRequest, session: Session = Depends(get_session)):
    credentials_exception = HTTPException(status_code=401, detail="invalid refresh token")
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception

    new_access_token = create_access_token({"sub": user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}


# TASK ROUTES (protected)


@app.post("/tasks", response_model=Task)
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


@app.get("/tasks", response_model=List[Task])
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


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    task = session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="task pas trouve")
    return task


@app.put("/tasks/{task_id}", response_model=Task)
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


@app.delete("/tasks/{task_id}")
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

#admin routes
@app.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/admin/tasks", response_model=List[Task])
async def get_all_tasks(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    tasks = session.exec(select(Task)).all()
    return tasks

@app.get("/admin/users", response_model=List[UserRead])
async def get_all_users(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    users = session.exec(select(User)).all()
    return users
BOOTSTRAP_ADMIN_KEY = os.getenv("BOOTSTRAP_ADMIN_KEY")

@app.post("/bootstrap-admin/{username}")
async def bootstrap_admin(
    username: str,
    secret_key: str,
    session: Session = Depends(get_session),
):
    if not BOOTSTRAP_ADMIN_KEY or secret_key != BOOTSTRAP_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="invalid bootstrap key")

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    user.is_admin = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": f"{username} is now admin"}
