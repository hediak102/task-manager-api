# Task Manager API

A REST API for managing personal tasks, built with FastAPI. Includes JWT authentication with refresh tokens, per-user data isolation, and role-based access control (admin/user).

**Live API docs:** https://task-manager-api-bwvp.onrender.com/docs

## Features

- Full CRUD for tasks (create, read, update, delete)
- JWT authentication with access + refresh tokens
- Password hashing with bcrypt
- Each user only sees and manages their own tasks
- Admin role with endpoints to view all tasks and all users
- Filtering (`completed=true/false`) and pagination (`skip`, `limit`) on task listing
- Database migrations managed with Alembic
- Automated test suite with pytest

## Tech Stack

- **FastAPI** — web framework
- **SQLModel** — ORM (SQLAlchemy + Pydantic)
- **PostgreSQL** (Neon) — database
- **Alembic** — schema migrations
- **python-jose** — JWT creation/verification
- **passlib[bcrypt]** — password hashing
- **pytest** + **httpx** — testing
- Deployed on **Render**

## Project Structure

```
task-manager-api/
├── main.py                 # app, models, routes
├── alembic/
│   ├── versions/            # migration files
│   └── env.py
├── alembic.ini
├── test_main.py             # automated test suite
├── requirements.txt
├── .env                      # local secrets (not committed)
└── .env.example              # template for required env vars
```

## Setup (local development)

1. Clone the repo and create a virtual environment:
   ```bash
   git clone <repo-url>
   cd task-manager-api
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example`:
   ```
   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
   DATABASE_URL=sqlite:///database.db
   ```
   (Leave `DATABASE_URL` unset to default to local SQLite, or point it at a PostgreSQL instance.)

4. Apply database migrations:
   ```bash
   alembic upgrade head
   ```

5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

6. Open the interactive docs at `http://127.0.0.1:8000/docs`.

## Running Tests

```bash
pytest -v
```

Tests run against an isolated in-memory SQLite database and never touch your local `database.db` or production data.

## Database Migrations

Whenever a model changes:

```bash
alembic revision --autogenerate -m "describe the change"
# review the generated file in alembic/versions/
alembic upgrade head
```

## API Overview

| Method | Route | Description | Auth required |
|---|---|---|---|
| POST | `/register` | Create a new user account | No |
| POST | `/login` | Log in, returns access + refresh tokens | No |
| POST | `/refresh` | Exchange a refresh token for a new access token | No |
| GET | `/me` | Get the current logged-in user's info | Yes |
| GET | `/tasks` | List your tasks (supports `skip`, `limit`, `completed`) | Yes |
| POST | `/tasks` | Create a task | Yes |
| GET | `/tasks/{id}` | Get a single task | Yes |
| PUT | `/tasks/{id}` | Update a task | Yes |
| DELETE | `/tasks/{id}` | Delete a task | Yes |
| GET | `/admin/tasks` | List all tasks (any user) | Admin only |
| GET | `/admin/users` | List all users | Admin only |

## Deployment

Deployed on Render as a Web Service, with PostgreSQL hosted on Neon.

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment variables required:** `SECRET_KEY`, `DATABASE_URL`

Migrations are applied automatically on every deploy, before the server starts.
