import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app, get_session

# In-memory test database — wiped every time
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

def get_test_session():
    with Session(engine) as session:
        yield session

# Swap the real DB dependency for the test one
app.dependency_overrides[get_session] = get_test_session

@pytest.fixture(autouse=True)
def setup_and_teardown():
    SQLModel.metadata.create_all(engine)   # fresh tables before each test
    yield
    SQLModel.metadata.drop_all(engine)     # wipe after each test

client = TestClient(app)


def test_create_task():
    response = client.post("/tasks", json={
        "title": "test task",
        "description": "just testing",
        "completed": False,
        "created_at": "12:00"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "test task"
    assert "id" in data


def test_create_task_empty_title_fails():
    response = client.post("/tasks", json={
        "title": "",
        "description": "bad",
        "completed": False,
        "created_at": "12:00"
    })
    assert response.status_code == 422


def test_get_tasks_empty():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_get_task_not_found():
    response = client.get("/tasks/999")
    assert response.status_code == 404


def test_full_crud_flow():
    # create
    create_resp = client.post("/tasks", json={
        "title": "wash dishes",
        "description": "do it",
        "completed": False,
        "created_at": "10:00"
    })
    task_id = create_resp.json()["id"]

    # read
    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "wash dishes"

    # update
    put_resp = client.put(f"/tasks/{task_id}", json={
        "title": "wash dishes NOW",
        "description": "urgent",
        "completed": True,
        "created_at": "10:00"
    })
    assert put_resp.status_code == 200
    assert put_resp.json()["completed"] is True

    # delete
    delete_resp = client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 200

    # confirm gone
    confirm_resp = client.get(f"/tasks/{task_id}")
    assert confirm_resp.status_code == 404