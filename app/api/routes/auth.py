from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.user import User, UserCreate
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter(tags=["auth"])

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register")
async def register(user: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(
        select(User).where(
            (User.username == user.username) | (User.email == user.email)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="username or email already taken")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "user created", "username": new_user.username, "email": new_user.email}

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="incorrect username or password")
    token = create_access_token({"sub": user.username})
    refresh_token = create_refresh_token({"sub": user.username})
    return {"access_token": token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh")
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