from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.conversa_canal import ConversaResponsavel, MensagemCanal
from app.models.mensagem import Mensagem
from app.models.usuario import Usuario
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


def test_conversas_paginadas_resumem_mensagens_e_filtram_sla():
    reset_db()
    with TestingSessionLocal() as db:
        customer = Cliente(id=1, nome="Marina Dias", telefone="+5521991112233")
        db.add(customer)
        db.flush()
        open_conversation = Conversa(cliente_id=customer.id, assunto="Retorno pendente", canal="whatsapp")
        closed_conversation = Conversa(cliente_id=customer.id, assunto="Atendimento encerrado", status="finalizada")
        db.add_all([open_conversation, closed_conversation])
        db.flush()
        old_time = datetime.utcnow() - timedelta(minutes=20)
        db.add_all([
            Mensagem(conversa_id=open_conversation.id, remetente="cliente", texto="Preciso de ajuda", data_envio=old_time),
            Mensagem(conversa_id=closed_conversation.id, remetente="cliente", texto="Já resolvido", data_envio=old_time),
        ])
        db.commit()

    response = client.get("/conversas/pagina?atrasadas=true")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["sla_minutes"] == 15
    assert payload["items"][0]["assunto"] == "Retorno pendente"
    assert payload["items"][0]["ultima_mensagem"] == "Preciso de ajuda"
    assert payload["items"][0]["sla_atrasada"] is True


def test_status_de_conversa_valida_transicoes():
    reset_db()
    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Carlos Silva"))
        db.commit()
    conversation_id = client.post("/conversas/", json={"cliente_id": 1}).json()["id"]

    finalized = client.patch(f"/conversas/{conversation_id}/status", json={"status": "finalizada"})
    assert finalized.status_code == 200
    invalid = client.patch(f"/conversas/{conversation_id}/status", json={"status": "pendente"})
    assert invalid.status_code == 409
    reopened = client.patch(f"/conversas/{conversation_id}/status", json={"status": "aberta"})
    assert reopened.status_code == 200


def test_atribuir_responsavel_e_rejeitar_usuario_inativo():
    reset_db()
    with TestingSessionLocal() as db:
        db.add_all([
            Cliente(id=1, nome="Ana Souza"),
            Usuario(username="agente", password_hash="hash", role="atendimento", ativo=True),
            Usuario(username="inativo", password_hash="hash", role="atendimento", ativo=False),
        ])
        db.commit()
    conversation_id = client.post("/conversas/", json={"cliente_id": 1}).json()["id"]

    assigned = client.patch(f"/conversas/{conversation_id}/responsavel", json={"username": "agente"})
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["responsavel"] == "agente"
    rejected = client.patch(f"/conversas/{conversation_id}/responsavel", json={"username": "inativo"})
    assert rejected.status_code == 422
    removed = client.patch(f"/conversas/{conversation_id}/responsavel", json={"username": None})
    assert removed.status_code == 200
    with TestingSessionLocal() as db:
        assert db.query(ConversaResponsavel).filter_by(conversa_id=conversation_id).count() == 0


def test_historico_de_mensagens_tem_paginacao_por_cursor():
    reset_db()
    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="João Lima"))
        db.commit()
    conversation_id = client.post("/conversas/", json={"cliente_id": 1}).json()["id"]
    for index in range(5):
        response = client.post(
            f"/conversas/{conversation_id}/mensagens/",
            json={"remetente": "cliente", "texto": f"Mensagem {index}"},
        )
        assert response.status_code == 201

    latest = client.get(f"/conversas/{conversation_id}/mensagens/pagina?limit=2")
    assert latest.status_code == 200, latest.text
    assert [item["texto"] for item in latest.json()["items"]] == ["Mensagem 3", "Mensagem 4"]
    assert latest.json()["has_more"] is True
    earlier = client.get(
        f"/conversas/{conversation_id}/mensagens/pagina?limit=2&before_id={latest.json()['next_before_id']}"
    )
    assert [item["texto"] for item in earlier.json()["items"]] == ["Mensagem 1", "Mensagem 2"]


def test_mensagem_whatsapp_registrada_com_id_do_provedor(monkeypatch):
    reset_db()
    with TestingSessionLocal() as db:
        db.add(Cliente(id=1, nome="Lia Ramos", telefone="+5521999990000"))
        db.commit()
    conversation_id = client.post(
        "/conversas/",
        json={"cliente_id": 1, "canal": "whatsapp"},
    ).json()["id"]
    monkeypatch.setattr("app.routers.conversa.send_whatsapp_text", lambda phone, text: "wamid.outbound")

    response = client.post(
        f"/conversas/{conversation_id}/mensagens/",
        json={"remetente": "atendente", "texto": "Olá!"},
    )
    assert response.status_code == 201, response.text
    with TestingSessionLocal() as db:
        provider_message = db.query(MensagemCanal).one()
        assert provider_message.provider_message_id == "wamid.outbound"
        assert provider_message.direction == "outbound"
