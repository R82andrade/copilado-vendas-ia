import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


bearer_scheme = HTTPBearer(auto_error=False)
ROLES = {"admin", "atendimento", "vendas", "leitor"}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


def auth_enabled() -> bool:
    return os.getenv("AUTH_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_auth_config() -> dict[str, str]:
    return {
        "username": os.getenv("ADMIN_USERNAME", "admin"),
        "password": os.getenv("ADMIN_PASSWORD", "admin123"),
        "secret": os.getenv("AUTH_SECRET") or os.getenv("ADMIN_TOKEN", "vendas-admin-token"),
    }


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_token(username: str, role: str) -> str:
    payload = json.dumps({"u": username, "r": role, "exp": int(time.time()) + 8 * 60 * 60}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(get_auth_config()["secret"].encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def decode_token(token: str) -> dict:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected = hmac.new(get_auth_config()["secret"].encode(), encoded.encode(), hashlib.sha256).digest()
        signature = base64.urlsafe_b64decode(supplied_signature + "=" * (-len(supplied_signature) % 4))
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload_bytes = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(payload_bytes)
        if payload["exp"] < int(time.time()) or payload["r"] not in ROLES:
            raise ValueError("expired or invalid role")
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")


def _allowed(role: str, method: str, path: str) -> bool:
    if role == "admin":
        return True
    if path == "/auth/agents":
        return method == "GET"
    if path == "/webhooks/whatsapp/status":
        return method == "GET"
    if role == "leitor":
        return method == "GET"
    if path.startswith("/conversas"):
        return role == "atendimento" or (role == "vendas" and method == "GET")
    if path.startswith("/clientes"):
        return method == "GET" or role == "vendas"
    if path.startswith("/ia"):
        return method == "GET" or role in {"atendimento", "vendas"}
    if path.startswith("/produtos") or path.startswith("/pedidos"):
        return method == "GET" or role == "vendas"
    return False


def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
):
    if not auth_enabled():
        return {"username": "local", "role": "admin"}

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticação obrigatório")

    configured_secret = get_auth_config()["secret"]
    if credentials.credentials == configured_secret:
        return {"username": get_auth_config()["username"], "role": "admin"}

    user = decode_token(credentials.credentials)
    from app.database import SessionLocal
    from app.models.usuario import Usuario

    db = SessionLocal()
    try:
        account = db.query(Usuario).filter(Usuario.username == user["u"], Usuario.ativo.is_(True)).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Conta desativada ou inexistente")
        role = account.role
    finally:
        db.close()

    if not _allowed(role, request.method, request.url.path):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seu perfil não tem permissão para esta ação")
    return {"username": user["u"], "role": role}
