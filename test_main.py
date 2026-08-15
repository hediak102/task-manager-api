import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from main import app, get_session,create_refresh_token

# In-memory test database — wiped every time
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

def get_test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

@pytest.fixture(autouse=True)
def setup_and_teardown():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

client = TestClient(app)


# ---------------------------------------------------------
# HELPER — évite de répéter register+login dans chaque test
# ---------------------------------------------------------

def create_and_login_user(username="hedi", password="hedi.2406"):
    client.post("/register", json={"username": username, "password": password})
    login_resp = client.post("/login", data={"username": username, "password": password})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------
# AUTH TESTS
# ---------------------------------------------------------

def test_register_user():
    response = client.post("/register", json={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_register_duplicate_username_fails():
    client.post("/register", json={"username": "alice", "password": "alicepass123"})
    response = client.post("/register", json={"username": "alice", "password": "autrepass"})
    assert response.status_code == 400


def test_login_success():
    client.post("/register", json={"username": "alice", "password": "alicepass123"})
    response = client.post("/login", data={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_fails():
    client.post("/register", json={"username": "alice", "password": "alicepass123"})
    response = client.post("/login", data={"username": "alice", "password": "mauvais_mdp"})
    assert response.status_code == 401


def test_login_nonexistent_user_fails():
    response = client.post("/login", data={"username": "personne", "password": "peuimporte"})
    assert response.status_code == 401


# ---------------------------------------------------------
# PROTECTED ROUTES — sans token
# ---------------------------------------------------------

def test_get_tasks_without_token_fails():
    response = client.get("/tasks")
    assert response.status_code == 401


def test_create_task_without_token_fails():
    response = client.post("/tasks", json={
        "title": "test", "description": "test", "completed": False, "created_at": "12:00"
    })
    assert response.status_code == 401


# ---------------------------------------------------------
# PROTECTED ROUTES — avec token valide
# ---------------------------------------------------------

def test_create_task_with_token():
    headers = create_and_login_user()
    response = client.post("/tasks", json={
        "title": "test task", "description": "just testing", "completed": False, "created_at": "12:00"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "test task"
    assert "id" in data


def test_get_tasks_empty_with_token():
    headers = create_and_login_user()
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_full_crud_flow_with_token():
    headers = create_and_login_user()

    create_resp = client.post("/tasks", json={
        "title": "wash dishes", "description": "do it", "completed": False, "created_at": "10:00"
    }, headers=headers)
    task_id = create_resp.json()["id"]

    get_resp = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "wash dishes"

    put_resp = client.put(f"/tasks/{task_id}", json={
        "title": "wash dishes NOW", "description": "urgent", "completed": True, "created_at": "10:00"
    }, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["completed"] is True

    delete_resp = client.delete(f"/tasks/{task_id}", headers=headers)
    assert delete_resp.status_code == 200

    confirm_resp = client.get(f"/tasks/{task_id}", headers=headers)
    assert confirm_resp.status_code == 404


# ---------------------------------------------------------
# ISOLATION ENTRE UTILISATEURS — le test le plus important
# ---------------------------------------------------------

def test_user_cannot_see_other_users_tasks():
    hedi_headers = create_and_login_user(username="hedi", password="hedi.2406")
    bob_headers = create_and_login_user(username="bob", password="bobpass123")

    # hedi crée une task
    create_resp = client.post("/tasks", json={
        "title": "hedi task", "description": "secret", "completed": False, "created_at": "10:00"
    }, headers=hedi_headers)
    hedi_task_id = create_resp.json()["id"]

    # bob ne doit rien voir dans sa liste
    bob_tasks = client.get("/tasks", headers=bob_headers)
    assert bob_tasks.json() == []

    # bob ne doit pas pouvoir accéder à la task de hedi par id
    bob_get = client.get(f"/tasks/{hedi_task_id}", headers=bob_headers)
    assert bob_get.status_code == 404

    # bob ne doit pas pouvoir la supprimer non plus
    bob_delete = client.delete(f"/tasks/{hedi_task_id}", headers=bob_headers)
    assert bob_delete.status_code == 404

    # hedi doit toujours pouvoir y accéder normalement
    hedi_get = client.get(f"/tasks/{hedi_task_id}", headers=hedi_headers)
    assert hedi_get.status_code == 200
# ---------------------------------------------------------
# REFRESH TOKEN TESTS
# ---------------------------------------------------------

def register_and_login_full(username="hedi", password="hedi.2406"):
    """Comme create_and_login_user, mais retourne les tokens bruts
    plutôt que le header, pour pouvoir manipuler refresh_token."""
    client.post("/register", json={"username": username, "password": password})
    login_resp = client.post("/login", data={"username": username, "password": password})
    return login_resp.json()


def test_login_returns_both_tokens():
    tokens = register_and_login_full()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_refresh_with_valid_token_returns_new_access_token():
    tokens = register_and_login_full()
    response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_new_access_token_from_refresh_works_on_protected_route():
    tokens = register_and_login_full()
    refresh_resp = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    new_access_token = refresh_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {new_access_token}"}
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200


def test_refresh_with_invalid_token_fails():
    response = client.post("/refresh", json={"refresh_token": "un_token_bidon_invalide"})
    assert response.status_code == 401


def test_refresh_with_access_token_instead_of_refresh_token_fails():
    """Un access_token ne doit pas pouvoir être utilisé comme refresh_token,
    grâce au check payload.get('type') != 'refresh'."""
    tokens = register_and_login_full()
    response = client.post("/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_refresh_with_nonexistent_user_fails():
    # On crée un refresh_token valide "à la main" pour un user qui n'existe pas en DB,
    # en réutilisant les fonctions internes de main.py
    fake_token = create_refresh_token({"sub": "utilisateur_qui_nexiste_pas"})
    response = client.post("/refresh", json={"refresh_token": fake_token})
    assert response.status_code == 401