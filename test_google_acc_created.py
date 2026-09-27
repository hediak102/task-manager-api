from sqlmodel import Session, select
from app.db.session import engine
from app.models.user import User

with Session(engine) as session:
    users = session.exec(select(User)).all()
    for u in users:
        print(u.username, u.email, u.oauth_provider, u.hashed_password)