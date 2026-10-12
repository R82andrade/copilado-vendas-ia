from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import LoginRequest, LoginResponse, ROLES, get_auth_config, hash_password, issue_token, require_auth, verify_password
from app.database import SessionLocal
from app.models.usuario import Usuario


router = APIRouter(prefix="/auth", tags=["Auth"])


class UsuarioCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=200)
    role: str


class UsuarioUpdate(BaseModel):
    role: str | None = None
    ativo: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=200)


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    ativo: bool


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _bootstrap_admin(db: Session) -> None:
    config = get_auth_config()
    account = db.query(Usuario).filter(Usuario.username == config["username"]).first()
    if account is None:
        db.add(Usuario(username=config["username"], password_hash=hash_password(config["password"]), role="admin", ativo=True))
        db.commit()
        return

    needs_sync = (
        account.role != "admin"
        or account.ativo is not True
        or not verify_password(config["password"], account.password_hash)
    )
    if needs_sync:
        account.role = "admin"
        account.ativo = True
        account.password_hash = hash_password(config["password"])
        db.commit()


def _require_admin(user: dict) -> None:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores podem gerenciar usuários")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    _bootstrap_admin(db)
    user = db.query(Usuario).filter(Usuario.username == payload.username).first()
    if not user or not user.ativo or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    config = get_auth_config()
    token = config["secret"] if user.username == config["username"] else issue_token(user.username, user.role)
    return LoginResponse(token=token, username=user.username, role=user.role)


@router.get("/users", response_model=list[UsuarioResponse])
def listar_usuarios(user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    _require_admin(user)
    return db.query(Usuario).order_by(Usuario.username).all()


@router.get("/agents", response_model=list[UsuarioResponse])
def listar_atendentes(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    return (
        db.query(Usuario)
        .filter(Usuario.ativo.is_(True), Usuario.role.in_(("admin", "atendimento")))
        .order_by(Usuario.username)
        .all()
    )


@router.post("/users", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(payload: UsuarioCreate, user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    _require_admin(user)
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {', '.join(sorted(ROLES))}")
    if db.query(Usuario).filter(Usuario.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Este usuário já existe")
    account = Usuario(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/users/{user_id}", response_model=UsuarioResponse)
def atualizar_usuario(user_id: int, payload: UsuarioUpdate, user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    _require_admin(user)
    account = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    loses_admin_access = account.role == "admin" and account.ativo and (
        payload.role not in (None, "admin") or payload.ativo is False
    )
    if loses_admin_access:
        active_admins = db.query(Usuario).filter(Usuario.role == "admin", Usuario.ativo.is_(True)).count()
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Mantenha ao menos um administrador ativo")
    if payload.role is not None:
        if payload.role not in ROLES:
            raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {', '.join(sorted(ROLES))}")
        account.role = payload.role
    if payload.ativo is not None:
        if account.username == user["username"] and not payload.ativo:
            raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta")
        account.ativo = payload.ativo
    if payload.password is not None:
        account.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(account)
    return account
