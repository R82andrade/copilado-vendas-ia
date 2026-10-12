from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_seed_demo_data():
    response = client.post("/demo/seed")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["clientes"] >= 1
    assert data["produtos"] >= 1
    assert data["conversas"] >= 1
    assert data["mensagens"] >= 1
