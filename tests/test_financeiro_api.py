from decimal import Decimal

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_auth
from app.database import Base
from app.main import app
from app.models.produto import Produto
from app.routers import financeiro as financeiro_router
from app.routers import ia as ia_router
from app.routers import produto as produto_router


@pytest.fixture
def financial_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_test_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    role = {"value": "admin"}
    previous = {
        financeiro_router.get_db: app.dependency_overrides.get(financeiro_router.get_db),
        ia_router.get_db: app.dependency_overrides.get(ia_router.get_db),
        produto_router.get_db: app.dependency_overrides.get(produto_router.get_db),
        require_auth: app.dependency_overrides.get(require_auth),
    }
    app.dependency_overrides[financeiro_router.get_db] = get_test_db
    app.dependency_overrides[ia_router.get_db] = get_test_db
    app.dependency_overrides[produto_router.get_db] = get_test_db
    app.dependency_overrides[require_auth] = lambda: {"username": "tester", "role": role["value"]}
    session = session_factory()
    product = Produto(
        nome="Notebook de teste", marca="Marca", categoria="Eletrônicos",
        preco=200, estoque=4, desconto_maximo=20,
    )
    session.add(product)
    session.commit()
    product_id = product.id
    session.close()
    try:
        yield TestClient(app), role, product_id, session_factory
    finally:
        for dependency, old_override in previous.items():
            if old_override is None:
                app.dependency_overrides.pop(dependency, None)
            else:
                app.dependency_overrides[dependency] = old_override
        engine.dispose()


def configure_product(client, product_id):
    response = client.put("/financeiro/configuracao", json={
        "imposto_variavel_percentual": "8",
        "comissao_percentual": "5",
        "margem_contribuicao_minima": "20",
        "limite_desconto_comercial": "15",
    })
    assert response.status_code == 200, response.text
    response = client.put(f"/financeiro/produtos/{product_id}", json={
        "custo_aquisicao": "100.00",
        "outros_custos_variaveis": "10.00",
    })
    assert response.status_code == 200, response.text


def test_finance_fields_are_never_in_public_product_responses(financial_client):
    client, role, product_id, _ = financial_client
    role["value"] = "leitor"
    collection = client.get("/produtos/")
    item = client.get(f"/produtos/{product_id}")
    assert collection.status_code == item.status_code == 200
    assert "custo_aquisicao" not in collection.text
    assert "margem_contribuicao_minima" not in item.text
    assert client.get(f"/financeiro/produtos/{product_id}").status_code == 403
    assert client.get("/financeiro/configuracao").status_code == 403


def test_sales_can_read_financial_calculation_but_cannot_edit_it(financial_client):
    client, role, product_id, _ = financial_client
    configure_product(client, product_id)
    role["value"] = "vendas"
    report = client.get(f"/financeiro/produtos/{product_id}")
    assert report.status_code == 200, report.text
    assert report.json()["situacao"] == "permitida"
    assert report.json()["preco_minimo"] == 164.18
    assert client.put(f"/financeiro/produtos/{product_id}", json={"custo_aquisicao": "80"}).status_code == 403
    assert client.put("/financeiro/configuracao", json={
        "imposto_variavel_percentual": "8", "comissao_percentual": "5",
        "margem_contribuicao_minima": "20", "limite_desconto_comercial": "15",
    }).status_code == 403


def test_missing_values_are_reported_and_product_values_override_store_defaults(financial_client):
    client, role, product_id, _ = financial_client
    role["value"] = "admin"
    incomplete = client.get(f"/financeiro/produtos/{product_id}").json()
    assert incomplete["situacao"] == "dados_insuficientes"
    assert "custo_aquisicao" in incomplete["dados_ausentes"]
    configure_product(client, product_id)
    client.put(f"/financeiro/produtos/{product_id}", json={
        "margem_contribuicao_minima": "25",
        "limite_desconto_comercial": "12",
    })
    result = client.get(f"/financeiro/produtos/{product_id}").json()
    assert result["preco_minimo"] == 177.42
    assert result["limite_comercial_desconto_percentual"] == 12


def test_discount_simulation_blocks_policy_and_financial_violations(financial_client):
    client, role, product_id, _ = financial_client
    configure_product(client, product_id)
    role["value"] = "vendas"
    blocked_commercial = client.post(f"/financeiro/produtos/{product_id}/simulacoes", json={
        "desconto_percentual": "16",
    })
    assert blocked_commercial.status_code == 200
    assert blocked_commercial.json()["situacao"] == "bloqueada"
    assert "comercial" in blocked_commercial.json()["motivo"]

    blocked_financial = client.post(f"/financeiro/produtos/{product_id}/simulacoes", json={
        "desconto_percentual": "20",
    })
    assert blocked_financial.json()["preco_final"] == 160
    assert "mínimo financeiro" in blocked_financial.json()["motivo"]

    target_price = client.post(f"/financeiro/produtos/{product_id}/simulacoes", json={
        "preco_final_pretendido": "180.00",
    })
    assert target_price.json()["situacao"] == "permitida"
    assert target_price.json()["desconto_percentual"] == Decimal("10.00")


def test_simulation_requires_one_valid_proposal(financial_client):
    client, _, product_id, _ = financial_client
    assert client.post(f"/financeiro/produtos/{product_id}/simulacoes", json={}).status_code == 422
    assert client.post(f"/financeiro/produtos/{product_id}/simulacoes", json={
        "desconto_percentual": "5", "preco_final_pretendido": "190",
    }).status_code == 422
    assert client.post(f"/financeiro/produtos/{product_id}/simulacoes", json={
        "desconto_percentual": "101",
    }).status_code == 422
    impossible_policy = client.put("/financeiro/configuracao", json={
        "imposto_variavel_percentual": 60,
        "comissao_percentual": 20,
        "margem_contribuicao_minima": 20,
        "limite_desconto_comercial": 10,
    })
    assert impossible_policy.status_code == 422


def test_financial_ai_requires_sales_permission_and_returns_insufficient_data_without_guessing(financial_client):
    client, role, product_id, _ = financial_client
    role["value"] = "atendimento"
    denied = client.post(f"/ia/produtos/{product_id}/recomendacao-financeira", json={})
    assert denied.status_code == 403
    role["value"] = "vendas"
    response = client.post(f"/ia/produtos/{product_id}/recomendacao-financeira", json={})
    assert response.status_code == 200
    assert response.json()["situacao"] == "dados_insuficientes"
    assert "dados financeiros suficientes" in response.json()["recomendacao"]


def test_financial_ai_explains_backend_facts_without_receiving_cost_values(financial_client, monkeypatch):
    client, role, product_id, _ = financial_client
    role["value"] = "admin"
    configure_product(client, product_id)
    role["value"] = "vendas"
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class AIResponse:
        status_code = 200
        is_error = False

        @staticmethod
        def json():
            return {"status": "completed", "output": [{"content": [
                {"type": "output_text", "text": "O desconto está dentro da política configurada."}
            ]}]}

    mocked_post = Mock(return_value=AIResponse())
    monkeypatch.setattr(ia_router.httpx, "post", mocked_post)
    response = client.post(f"/ia/produtos/{product_id}/recomendacao-financeira", json={"desconto_percentual": 10})
    assert response.status_code == 200, response.text
    assert response.json()["situacao"] == "permitida", response.text
    assert response.json()["revisao_humana_necessaria"] is True
    request_text = mocked_post.call_args.kwargs["json"]["input"][1]["content"][0]["text"]
    assert "preco_minimo" in request_text
    assert "custo_aquisicao" not in request_text
