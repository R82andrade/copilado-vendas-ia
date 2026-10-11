from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    assunto: Mapped[str] = mapped_column(String(200), nullable=False, default="Atendimento")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="aberta")
    canal: Mapped[str] = mapped_column(String(50), nullable=False, default="chat")
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    ultima_atualizacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="conversas")
    mensagens: Mapped[list["Mensagem"]] = relationship(
        back_populates="conversa",
        cascade="all, delete-orphan",
    )
