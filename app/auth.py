import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


def auth_enabled() -> bool:
    return os.getenv("AUTH_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_auth_config() -> dict:
    return {
        "username": os.getenv("ADMIN_USERNAME", "admin"),
        "password": os.getenv("ADMIN_PASSWORD", "admin123"),
        "token": os.getenv("ADMIN_TOKEN", "vendas-admin-token"),
    }


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
):
    if not auth_enabled():
        return None

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação obrigatório",
        )

    expected = get_auth_config()["token"]
    if credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    return credentials.credentials
