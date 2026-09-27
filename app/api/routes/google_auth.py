from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session, select

from app.core.oauth import oauth
from app.db.session import get_session
from app.models.user import User
from app.core.security import create_access_token, create_refresh_token

router = APIRouter(tags=["google-auth"])


@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, session: Session = Depends(get_session)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="could not retrieve email from Google")

    email = user_info["email"]
    existing_user = session.exec(select(User).where(User.email == email)).first()

    if existing_user:
        user = existing_user
    else:
        # génère un username unique basé sur l'email
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while session.exec(select(User).where(User.username == username)).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            hashed_password=None,
            oauth_provider="google",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    access_token = create_access_token({"sub": user.username})
    refresh_token = create_refresh_token({"sub": user.username})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}