import os

import httpx


class WhatsAppSendError(Exception):
    pass


def whatsapp_is_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in ("META_ACCESS_TOKEN", "META_PHONE_NUMBER_ID")
    )


def send_whatsapp_text(phone: str, text: str) -> str:
    access_token = os.getenv("META_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID", "").strip()
    if not access_token or not phone_number_id:
        raise WhatsAppSendError(
            "Envio WhatsApp indisponível. Configure META_ACCESS_TOKEN e META_PHONE_NUMBER_ID."
        )

    version = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip()
    destination = "".join(character for character in phone if character.isdigit())
    if not destination:
        raise WhatsAppSendError("O telefone do cliente não é válido para WhatsApp.")

    try:
        response = httpx.post(
            f"https://graph.facebook.com/{version}/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": destination,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            },
            timeout=20.0,
        )
    except httpx.RequestError as exc:
        raise WhatsAppSendError("Não foi possível conectar à API do WhatsApp.") from exc

    if response.is_error:
        try:
            error = response.json().get("error", {})
            code = error.get("code")
        except (ValueError, AttributeError):
            code = None
        detail = f" (código {code})" if code is not None else ""
        raise WhatsAppSendError(f"A Meta recusou o envio da mensagem{detail}.")

    try:
        messages = response.json().get("messages", [])
        message_id = messages[0].get("id") if messages else None
    except (ValueError, AttributeError, IndexError, TypeError):
        message_id = None
    if not message_id:
        raise WhatsAppSendError("A Meta não confirmou o envio da mensagem.")
    return message_id
