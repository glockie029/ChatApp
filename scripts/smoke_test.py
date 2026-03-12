from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from db.session import Base, get_db


def assert_equal(actual, expected, message):
    if actual != expected:
        raise SystemExit(f"{message}: expected={expected!r}, actual={actual!r}")


def assert_true(condition, message):
    if not condition:
        raise SystemExit(message)


def build_client(enable_unsafe_routes):
    temp_dir = TemporaryDirectory()
    db_path = Path(temp_dir.name) / "smoke.db"
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

    app = main.create_app(enable_unsafe_routes=enable_unsafe_routes)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, temp_dir


def run_safe_mode_checks():
    client, temp_dir = build_client(enable_unsafe_routes=False)

    try:
        root = client.get("/")
        assert_equal(root.status_code, 200, "root status code mismatch")
        assert_equal(root.json()["unsafe_routes_enabled"], False, "safe mode should disable unsafe routes")

        created = client.post(
            "/messages/",
            json={"username": " audit-user ", "content": " rotate secret now "},
        )
        assert_equal(created.status_code, 201, "create message status code mismatch")
        created_payload = created.json()
        assert_equal(created_payload["username"], "audit-user", "username should be trimmed")
        assert_true("secret" in created_payload["risk_tags"], "risk tags should include secret")

        search = client.get("/messages/search", params={"keyword": "secret"})
        assert_equal(search.status_code, 200, "search status code mismatch")
        assert_true(len(search.json()) >= 1, "search should return at least one message")

        health = client.get("/health")
        assert_equal(health.status_code, 200, "health status code mismatch")
        assert_equal(health.json()["unsafe_routes_enabled"], False, "health should report safe mode")
    finally:
        client.close()
        temp_dir.cleanup()


def run_training_mode_checks():
    client, temp_dir = build_client(enable_unsafe_routes=True)

    try:
        unsafe_insert = client.post(
            "/unsafe_messages/",
            json={"username": "trainer", "content": "unsafe insert demo"},
        )
        assert_equal(unsafe_insert.status_code, 201, "unsafe insert status code mismatch")

        unsafe_search = client.get("/unsafe_search/", params={"query": "unsafe"})
        assert_equal(unsafe_search.status_code, 200, "unsafe search status code mismatch")
        assert_true("result" in unsafe_search.json(), "unsafe search should return result field")
    finally:
        client.close()
        temp_dir.cleanup()


if __name__ == "__main__":
    run_safe_mode_checks()
    run_training_mode_checks()
    print("smoke test passed")
