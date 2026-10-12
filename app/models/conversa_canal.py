from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversaResponsavel(Base):
    __tablename__ = "conversas_responsaveis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversa_id: Mapped[int] = mapped_column(
        ForeignKey("conversas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    atribuido_por: Mapped[str] = mapped_column(String(80), nullable=False)
    atribuido_em: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class MensagemCanal(Base):
    __tablename__ = "mensagens_canais"
    __table_args__ = (
        UniqueConstraint("provider", "provider_message_id", name="uq_provider_message"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mensagem_id: Mapped[int] = mapped_column(
        ForeignKey("mensagens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(200), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="accepted")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
