from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from db.session import Base, get_db


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["unsafe_routes_enabled"] is False


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "ChatApp DevSecOps API"


def test_create_message_normalizes_input_and_returns_risk_tags(client: TestClient):
    response = client.post(
        "/messages/",
        json={"username": "  ", "content": "  rotate password quickly  "},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "Anonymous"
    assert data["content"] == "rotate password quickly"
    assert "password" in data["risk_tags"]


def test_get_message_by_id(client: TestClient):
    created = client.post(
        "/messages/",
        json={"username": "TestUser", "content": "Hello DevSecOps"},
    )
    message_id = created.json()["id"]

    response = client.get(f"/messages/{message_id}")
    assert response.status_code == 200
    assert response.json()["id"] == message_id


def test_search_messages(client: TestClient):
    client.post("/messages/", json={"username": "alice", "content": "deploy done"})
    client.post("/messages/", json={"username": "bob", "content": "security review"})

    response = client.get("/messages/search", params={"keyword": "deploy"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "deploy done"


def test_moderation_summary_counts_flagged_messages(client: TestClient):
    client.post("/messages/", json={"username": "alice", "content": "public message"})
    client.post("/messages/", json={"username": "bob", "content": "never share your token"})

    response = client.get("/moderation/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_messages"] == 2
    assert data["flagged_messages"] == 1


def test_unsafe_routes_disabled_by_default(client: TestClient):
    response = client.get("/unsafe_search/", params={"query": "test"})
    assert response.status_code == 404


def test_unsafe_routes_can_be_enabled_for_training():
    training_app = main.create_app(enable_unsafe_routes=True)
    with TestClient(training_app) as training_client:
        health_response = training_client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["unsafe_routes_enabled"] is True
