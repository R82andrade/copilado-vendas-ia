from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_cadastro: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")
    conversas: Mapped[list["Conversa"]] = relationship(back_populates="cliente")
