from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.models.usuario import Usuario
from app.routers.auth import get_db


client = TestClient(app)


def test_login_retorna_token(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha123")
    monkeypatch.setenv("ADMIN_TOKEN", "token-secreto")

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "senha123"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["token"] == "token-secreto"


def test_rota_protegida_requer_token(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha123")
    monkeypatch.setenv("ADMIN_TOKEN", "token-secreto")

    response = client.get("/conversas/")
    assert response.status_code == 401


def test_login_redefine_admin_quando_hash_esta_desatualizado(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("ADMIN_TOKEN", "token-secreto")

    from app.database import SessionLocal
    from app.models.usuario import Usuario

    session = SessionLocal()
    user = session.query(Usuario).filter(Usuario.username == "admin").first()
    if user:
        user.password_hash = "pbkdf2_sha256$old$salt-invalid"
        user.role = "admin"
        user.ativo = True
        session.commit()
    session.close()

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["username"] == "admin"


def test_listar_atendentes_ativos(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    with testing_session() as db:
        db.add_all([
            Usuario(username="admin-active", password_hash="hash", role="admin", ativo=True),
            Usuario(username="agent-active", password_hash="hash", role="atendimento", ativo=True),
            Usuario(username="agent-inactive", password_hash="hash", role="atendimento", ativo=False),
            Usuario(username="sales-active", password_hash="hash", role="vendas", ativo=True),
        ])
        db.commit()

    response = client.get("/auth/agents")
    assert response.status_code == 200, response.text
    assert [user["username"] for user in response.json()] == ["admin-active", "agent-active"]
