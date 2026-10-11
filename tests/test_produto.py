from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.routers.produto import get_db


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


def test_criar_produto_valido():
    reset_db()

    payload = {
        "nome": "Notebook Pro",
        "marca": "TechMax",
        "categoria": "Eletrônicos",
        "preco": 2499.90,
        "estoque": 12,
        "desconto_maximo": 15,
    }

    response = client.post("/produtos/", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["nome"] == "Notebook Pro"
    assert data["marca"] == "TechMax"
    assert data["categoria"] == "Eletrônicos"
    assert data["preco"] == 2499.9
    assert data["estoque"] == 12
    assert data["desconto_maximo"] == 15


def test_validar_preco_positivo():
    reset_db()

    payload = {
        "nome": "Teclado",
        "marca": "BrandX",
        "categoria": "Periféricos",
        "preco": 0,
        "estoque": 5,
        "desconto_maximo": 10,
    }

    response = client.post("/produtos/", json=payload)

    assert response.status_code == 422


def test_validar_desconto_maximo():
    reset_db()

    payload = {
        "nome": "Mouse",
        "marca": "BrandX",
        "categoria": "Periféricos",
        "preco": 99.90,
        "estoque": 8,
        "desconto_maximo": 101,
    }

    response = client.post("/produtos/", json=payload)

    assert response.status_code == 422


def test_listar_produtos():
    reset_db()

    client.post(
        "/produtos/",
        json={
            "nome": "Monitor",
            "marca": "Vision",
            "categoria": "Eletrônicos",
            "preco": 899.00,
            "estoque": 4,
            "desconto_maximo": 20,
        },
    )

    response = client.get("/produtos/")

    assert response.status_code == 200
    assert len(response.json()) == 1
