import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.conversa_canal import MensagemCanal
from app.models.mensagem import Mensagem


router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_phone(phone: str | None) -> str:
    return "".join(character for character in (phone or "") if character.isdigit())


@router.get("/status")
def whatsapp_status(user: dict = Depends(require_auth)):
    return {
        "configured": all(
            os.getenv(name, "").strip()
            for name in (
                "META_ACCESS_TOKEN",
                "META_PHONE_NUMBER_ID",
                "META_APP_SECRET",
                "META_VERIFY_TOKEN",
            )
        )
    }


def _contact_name(contacts: list[dict], phone: str) -> str | None:
    for contact in contacts:
        if normalize_phone(contact.get("wa_id")) == phone:
            name = contact.get("profile", {}).get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()[:150]
    return None


@router.get("", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    expected_token = os.getenv("META_VERIFY_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(status_code=503, detail="Configure META_VERIFY_TOKEN antes de verificar o webhook.")
    if mode != "subscribe" or not challenge or not hmac.compare_digest(verify_token or "", expected_token):
        raise HTTPException(status_code=403, detail="Verificação do webhook recusada.")
    return challenge


@router.post("")
async def receive_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    app_secret = os.getenv("META_APP_SECRET", "").strip()
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID", "").strip()
    if not app_secret or not phone_number_id:
        raise HTTPException(
            status_code=503,
            detail="Configure META_APP_SECRET e META_PHONE_NUMBER_ID antes de receber mensagens.",
        )

    body = await request.body()
    supplied_signature = request.headers.get("X-Hub-Signature-256", "")
    expected_signature = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Assinatura do webhook inválida.")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Payload JSON inválido.") from exc

    received = 0
    duplicates = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata_id = value.get("metadata", {}).get("phone_number_id")
            if metadata_id != phone_number_id:
                continue
            contacts = value.get("contacts", [])
            for incoming in value.get("messages", []):
                provider_id = incoming.get("id")
                sender = normalize_phone(incoming.get("from"))
                text_body = incoming.get("text", {}).get("body")
                if not provider_id or not sender or not isinstance(text_body, str) or not text_body.strip():
                    continue
                existing = db.query(MensagemCanal.id).filter(
                    MensagemCanal.provider == "whatsapp",
                    MensagemCanal.provider_message_id == provider_id,
                ).first()
                if existing:
                    duplicates += 1
                    continue

                matching_clients = db.query(Cliente).filter(Cliente.telefone.isnot(None)).all()
                customer = next(
                    (item for item in matching_clients if normalize_phone(item.telefone) == sender),
                    None,
                )
                if customer is None:
                    customer = Cliente(
                        nome=_contact_name(contacts, sender) or f"WhatsApp {sender}",
                        telefone=f"+{sender}",
                    )
                    db.add(customer)
                    db.flush()

                conversation = (
                    db.query(Conversa)
                    .filter(
                        Conversa.cliente_id == customer.id,
                        Conversa.canal == "whatsapp",
                        Conversa.status != "finalizada",
                    )
                    .order_by(Conversa.ultima_atualizacao.desc())
                    .first()
                )
                if conversation is None:
                    conversation = Conversa(
                        cliente_id=customer.id,
                        assunto="Atendimento via WhatsApp",
                        canal="whatsapp",
                        status="aberta",
                    )
                    db.add(conversation)
                    db.flush()

                timestamp = incoming.get("timestamp")
                if isinstance(timestamp, str) and timestamp.isdigit():
                    sent_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).replace(tzinfo=None)
                else:
                    sent_at = datetime.utcnow()
                message = Mensagem(
                    conversa_id=conversation.id,
                    remetente="cliente",
                    texto=text_body.strip()[:4000],
                    data_envio=sent_at,
                )
                conversation.ultima_atualizacao = sent_at
                db.add(message)
                db.flush()
                db.add(MensagemCanal(
                    mensagem_id=message.id,
                    provider="whatsapp",
                    provider_message_id=provider_id,
                    direction="inbound",
                ))
                db.commit()
                received += 1

    return {"status": "ok", "received": received, "duplicates": duplicates}
