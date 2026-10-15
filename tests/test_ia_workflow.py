import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.mensagem import Mensagem
from app.routers import conversa as conversa_router
from app.routers import ia as ia_router


@pytest.fixture
def workflow_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = test_session()
    client_record = Cliente(nome="Cliente teste")
    session.add(client_record)
    session.flush()
    conversation = Conversa(cliente_id=client_record.id, assunto="Interesse em produto")
    session.add(conversation)
    session.flush()
    session.add(Mensagem(conversa_id=conversation.id, remetente="cliente", texto="Quero saber mais."))
    session.commit()
    conversation_id = conversation.id
    session.close()

    def get_test_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[ia_router.get_db] = get_test_db
    app.dependency_overrides[conversa_router.get_db] = get_test_db
    try:
        yield TestClient(app), test_session, conversation_id
    finally:
        app.dependency_overrides.pop(ia_router.get_db, None)
        app.dependency_overrides.pop(conversa_router.get_db, None)
        engine.dispose()


def test_analysis_suggestions_and_seller_decisions_are_persisted(workflow_client, monkeypatch):
    client, test_session, conversation_id = workflow_client
    analysis = {
        "intencao": "Avaliar uma compra",
        "justificativa_intencao": "O cliente pediu detalhes.",
        "objecoes": ["Preço"],
        "produtos_recomendados": ["Produto teste"],
        "evidencias": ["Quero saber mais."],
        "resposta_sugerida": "Posso explicar as opções disponíveis.",
        "confianca": "media",
    }

    class OpenAIResponse:
        is_error = False
        status_code = 200

        @staticmethod
        def json():
            return {
                "status": "completed",
                "output": [{"content": [{"type": "output_text", "text": json.dumps(analysis)}]}],
            }

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ia_router.httpx, "post", Mock(return_value=OpenAIResponse()))

    response = client.post(f"/ia/conversas/{conversation_id}/analise")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["analise"]["intencao"] == analysis["intencao"]
    assert {item["tipo"] for item in result["sugestoes"]} == {"produto", "resposta"}

    response_suggestion = next(item for item in result["sugestoes"] if item["tipo"] == "resposta")
    product_suggestion = next(item for item in result["sugestoes"] if item["tipo"] == "produto")
    accepted = client.post(
        f"/ia/sugestoes/{response_suggestion['id']}/decisao",
        json={"decisao": "aceita"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "aceita"

    sent = client.post(
        f"/conversas/{conversation_id}/mensagens/",
        json={
            "remetente": "atendente",
            "texto": "Resposta revisada pelo vendedor.",
            "sugestao_id": response_suggestion["id"],
        },
    )
    assert sent.status_code == 201, sent.text

    rejected = client.post(
        f"/ia/sugestoes/{product_suggestion['id']}/decisao",
        json={"decisao": "rejeitada"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejeitada"

    history = client.get("/ia/analises")
    assert history.status_code == 200, history.text
    saved_analysis = history.json()[0]
    assert saved_analysis["criado_por"] == "local"
    assert saved_analysis["sugestoes"]

    saved_suggestions = client.get("/ia/sugestoes").json()
    saved_response = next(item for item in saved_suggestions if item["id"] == response_suggestion["id"])
    assert saved_response["status"] == "enviada"
    assert [item["decisao"] for item in saved_response["decisoes"]] == ["aceita", "enviada"]
    assert saved_response["decisoes"][-1]["texto_enviado"] == "Resposta revisada pelo vendedor."

    session = test_session()
    saved_message = session.query(Mensagem).filter(Mensagem.id == saved_response["decisoes"][-1]["mensagem_id"]).one()
    assert saved_message.texto == "Resposta revisada pelo vendedor."
    session.close()


def test_message_cannot_mark_an_unaccepted_suggestion_as_sent(workflow_client, monkeypatch):
    client, _, conversation_id = workflow_client
    analysis = {
        "intencao": "Informação",
        "justificativa_intencao": "Pergunta do cliente.",
        "objecoes": [],
        "produtos_recomendados": [],
        "evidencias": [],
        "resposta_sugerida": "Resposta sugerida.",
        "confianca": "baixa",
    }

    class OpenAIResponse:
        is_error = False
        status_code = 200

        @staticmethod
        def json():
            return {
                "status": "completed",
                "output": [{"content": [{"type": "output_text", "text": json.dumps(analysis)}]}],
            }

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ia_router.httpx, "post", Mock(return_value=OpenAIResponse()))
    analyzed = client.post(f"/ia/conversas/{conversation_id}/analise")
    suggestion = next(item for item in analyzed.json()["sugestoes"] if item["tipo"] == "resposta")

    response = client.post(
        f"/conversas/{conversation_id}/mensagens/",
        json={"remetente": "atendente", "texto": "Não enviada.", "sugestao_id": suggestion["id"]},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "A sugestão deve ser aceita antes de registrar o envio."
