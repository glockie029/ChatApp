from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Anonymous Chat API is running"}

def test_create_message():
    response = client.post(
        '/messages/',
        json={"username":"TestUser","content":"Hello DevSecOps"}
        )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "TestUser"
    assert data["content"] == "Hello DevSecOps"
    assert "id" in data

def test_get_messages():
    response = client.get("/messages/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)