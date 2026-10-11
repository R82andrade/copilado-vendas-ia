import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

raw_database_url = os.getenv("DATABASE_URL")
if raw_database_url and "SUA_SENHA" in raw_database_url:
    raw_database_url = None

DATABASE_URL = raw_database_url or "sqlite:///./copiloto_vendas.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


from app.models.cliente import Cliente  # noqa: E402,F401
from app.models.pedido import ItemPedido, Pedido  # noqa: E402,F401
from app.models.produto import Produto  # noqa: E402,F401

Base.metadata.create_all(bind=engine)
