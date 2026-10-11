from fastapi import APIRouter, HTTPException, status

from app.auth import LoginRequest, LoginResponse, auth_enabled, get_auth_config


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    config = get_auth_config()

    if not auth_enabled():
        return LoginResponse(token=config["token"], username=payload.username)

    if payload.username != config["username"] or payload.password != config["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    return LoginResponse(token=config["token"], username=payload.username)
