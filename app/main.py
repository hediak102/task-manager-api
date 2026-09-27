from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, tasks, admin,google_auth
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import SECRET_KEY
app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
origins = [
    "http://localhost:5173",
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

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(admin.router)
app.include_router(google_auth.router)
@app.get("/")
async def read_root():
    return {"message": "api is running"}