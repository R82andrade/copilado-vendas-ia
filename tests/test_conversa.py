from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.cliente import Cliente
from app.routers.conversa import get_db


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


def test_criar_conversa_e_registrar_mensagem():
    reset_db()

    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Lucas Almeida", telefone="21991112233", cpf="12312312388"))
        db.commit()

    conversa_payload = {
        "cliente_id": 1,
        "assunto": "Dúvida sobre pedido",
        "status": "aberta",
        "canal": "chat",
    }

    response = client.post("/conversas/", json=conversa_payload)
    assert response.status_code == 201, response.text
    conversa = response.json()
    assert conversa["cliente_id"] == 1
    assert conversa["assunto"] == "Dúvida sobre pedido"

    mensagem_payload = {
        "remetente": "cliente",
        "texto": "Olá, quero acompanhar meu pedido.",
    }

    mensagem_response = client.post(
        f"/conversas/{conversa['id']}/mensagens/",
        json=mensagem_payload,
    )
    assert mensagem_response.status_code == 201, mensagem_response.text
    assert mensagem_response.json()["texto"] == "Olá, quero acompanhar meu pedido."

    list_response = client.get(f"/conversas/{conversa['id']}/mensagens/")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_listar_conversas_do_cliente():
    reset_db()

    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Beatriz Costa", telefone="21992223344", cpf="44455566677"))
        db.commit()

    client.post(
        "/conversas/",
        json={"cliente_id": 1, "assunto": "Troca de produto", "status": "pendente", "canal": "whatsapp"},
    )

    response = client.get("/conversas/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_atualizar_status_e_filtrar_conversas():
    reset_db()

    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Lucas Rocha", telefone="21993334455", cpf="10111213141"))
        db.commit()

    client.post(
        "/conversas/",
        json={"cliente_id": 1, "assunto": "Pedido atrasado", "status": "aberta", "canal": "whatsapp"},
    )
    client.post(
        "/conversas/",
        json={"cliente_id": 1, "assunto": "Consulta de estoque", "status": "pendente", "canal": "chat"},
    )

    update_response = client.patch(
        "/conversas/1/status",
        json={"status": "em_atendimento"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "em_atendimento"

    filtro_status = client.get("/conversas/?status=em_atendimento")
    assert filtro_status.status_code == 200
    assert len(filtro_status.json()) == 1

    filtro_cliente = client.get("/conversas/?cliente_id=1")
    assert filtro_cliente.status_code == 200
    assert len(filtro_cliente.json()) == 2
