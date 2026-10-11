from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.cliente import Cliente
from app.routers.cliente import get_db


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_criar_cliente():
    cliente = Cliente(
        id=1,
        nome="João Pedro",
        telefone="21999999999",
        data_cadastro=date.today()
    )

    assert cliente.nome == "João Pedro"
    assert cliente.cpf is None
    assert cliente.email is None


def test_api_criar_e_listar_clientes():
    reset_db()

    payload = {
        "nome": "Maria Silva",
        "cpf": "12345678909",
        "telefone": "21998877666",
        "email": "maria@email.com",
    }

    response = client.post("/clientes/", json=payload)
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["nome"] == "Maria Silva"
    assert data["cpf"] == "12345678909"

    list_response = client.get("/clientes/")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1


def test_api_atualizar_cliente():
    reset_db()

    payload = {
        "nome": "Pedro Santos",
        "cpf": "98765432100",
        "telefone": "21997778888",
        "email": "pedro@email.com",
    }

    create_response = client.post("/clientes/", json=payload)
    cliente_id = create_response.json()["id"]

    update_response = client.put(
        f"/clientes/{cliente_id}",
        json={
            "nome": "Pedro Atualizado",
            "telefone": "21990001122",
            "email": "pedro.novo@email.com",
        },
    )

    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["nome"] == "Pedro Atualizado"
    assert update_response.json()["email"] == "pedro.novo@email.com"
