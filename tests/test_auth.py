from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_retorna_token(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha123")
    monkeypatch.setenv("ADMIN_TOKEN", "token-secreto")

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "senha123"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["token"] == "token-secreto"


def test_rota_protegida_requer_token(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha123")
    monkeypatch.setenv("ADMIN_TOKEN", "token-secreto")

    response = client.get("/conversas/")
    assert response.status_code == 401
