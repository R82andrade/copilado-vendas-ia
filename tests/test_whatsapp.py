import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.conversa_canal import MensagemCanal
from app.models.mensagem import Mensagem
from app.routers.whatsapp import get_db


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


def _signed_headers(body: bytes, secret: str) -> dict[str, str]:
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={signature}"}


def test_webhook_whatsapp_verifica_assinatura_deduplica_e_cadastra_contato(monkeypatch):
    reset_db()
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "phone-number-123")
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": "phone-number-123"},
                    "contacts": [{
                        "wa_id": "5521998887766",
                        "profile": {"name": "Paula Nunes"},
                    }],
                    "messages": [{
                        "id": "wamid.inbound",
                        "from": "5521998887766",
                        "timestamp": "1700000000",
                        "type": "text",
                        "text": {"body": "Tenho interesse no produto"},
                    }],
                },
            }],
        }],
    }
    body = json.dumps(payload).encode()
    headers = _signed_headers(body, "test-app-secret")

    invalid = client.post("/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": "sha256=invalid"})
    assert invalid.status_code == 401
    received = client.post("/webhooks/whatsapp", content=body, headers=headers)
    assert received.status_code == 200, received.text
    assert received.json() == {"status": "ok", "received": 1, "duplicates": 0}
    duplicate = client.post("/webhooks/whatsapp", content=body, headers=headers)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json() == {"status": "ok", "received": 0, "duplicates": 1}

    with TestingSessionLocal() as db:
        customer = db.query(Cliente).one()
        conversation = db.query(Conversa).one()
        message = db.query(Mensagem).one()
        provider_message = db.query(MensagemCanal).one()
        assert customer.nome == "Paula Nunes"
        assert customer.telefone == "+5521998887766"
        assert conversation.canal == "whatsapp"
        assert message.texto == "Tenho interesse no produto"
        assert provider_message.provider_message_id == "wamid.inbound"
