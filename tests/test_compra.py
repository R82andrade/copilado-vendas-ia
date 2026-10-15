from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.cliente import Cliente
from app.models.configuracao_financeira import ConfiguracaoFinanceira
from app.models.produto import Produto
from app.routers.pedido import get_db


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
    with TestingSessionLocal() as db:
        db.add(ConfiguracaoFinanceira(
            id=1, imposto_variavel_percentual=0, comissao_percentual=0,
            margem_contribuicao_minima=20, limite_desconto_comercial=20,
        ))
        db.commit()


def test_criar_pedido_com_itens():
    reset_db()

    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Ana Souza", telefone="21998887766", cpf="11122233344"))
        db.add(
            Produto(
                id=1,
                nome="Cafeteira",
                marca="Aroma",
                categoria="Casa",
                preco=299.90,
                estoque=10,
                desconto_maximo=15,
                custo_aquisicao=100,
                outros_custos_variaveis=0,
            )
        )
        db.commit()

    payload = {
        "cliente_id": 1,
        "itens": [
            {"produto_id": 1, "quantidade": 2, "desconto": 10},
        ],
    }

    response = client.post("/pedidos/", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["cliente_id"] == 1
    assert data["total"] == 539.82
    assert len(data["itens"]) == 1
    assert data["itens"][0]["quantidade"] == 2


def test_pedido_nao_permite_desconto_acima_do_maximo():
    reset_db()

    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Bruno", telefone="21997776655", cpf="55544433322"))
        db.add(
            Produto(
                id=1,
                nome="Ventilador",
                marca="AirFlow",
                categoria="Casa",
                preco=150.00,
                estoque=7,
                desconto_maximo=10,
                custo_aquisicao=100,
                outros_custos_variaveis=0,
            )
        )
        db.commit()

    payload = {
        "cliente_id": 1,
        "itens": [
            {"produto_id": 1, "quantidade": 1, "desconto": 25},
        ],
    }

    response = client.post("/pedidos/", json=payload)

    assert response.status_code == 400


def test_pedido_bloqueia_desconto_acima_do_limite_financeiro():
    reset_db()
    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Lia"))
        db.add(Produto(
            id=1, nome="Produto", marca="Marca", categoria="Teste", preco=150,
            estoque=2, desconto_maximo=20, custo_aquisicao=100,
            outros_custos_variaveis=0,
        ))
        db.commit()
    response = client.post("/pedidos/", json={
        "cliente_id": 1,
        "itens": [{"produto_id": 1, "quantidade": 1, "desconto": 18}],
    })
    assert response.status_code == 400
    assert "mínimo financeiro" in response.json()["detail"]


def test_pedido_sem_dados_financeiros_nao_aceita_desconto_positivo():
    reset_db()
    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Caio"))
        db.add(Produto(
            id=1, nome="Produto", marca="Marca", categoria="Teste", preco=150,
            estoque=2, desconto_maximo=20,
        ))
        db.commit()
    response = client.post("/pedidos/", json={
        "cliente_id": 1,
        "itens": [{"produto_id": 1, "quantidade": 1, "desconto": 5}],
    })
    assert response.status_code == 422
    assert "dados financeiros ausentes" in response.json()["detail"]


def test_listar_historico_de_compras():
    reset_db()

    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Carlos", telefone="21990001122", cpf="99988877766"))
        db.add(
            Produto(
                id=1,
                nome="Liquidificador",
                marca="Mix",
                categoria="Casa",
                preco=180.00,
                estoque=5,
                desconto_maximo=20,
                custo_aquisicao=100,
                outros_custos_variaveis=0,
            )
        )
        db.commit()

    client.post(
        "/pedidos/",
        json={
            "cliente_id": 1,
            "itens": [{"produto_id": 1, "quantidade": 1, "desconto": 5}],
        },
    )

    response = client.get("/pedidos/")

    assert response.status_code == 200
    assert len(response.json()) == 1
