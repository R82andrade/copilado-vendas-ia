from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AnaliseIA(Base):
    __tablename__ = "analises_ia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id"), nullable=False, index=True)
    criado_por: Mapped[str] = mapped_column(String(80), nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    intencao: Mapped[str] = mapped_column(Text, nullable=False)
    justificativa_intencao: Mapped[str] = mapped_column(Text, nullable=False)
    objecoes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    produtos_recomendados: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidencias: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    resposta_sugerida: Mapped[str] = mapped_column(Text, nullable=False)
    confianca: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    sugestoes: Mapped[list["SugestaoIA"]] = relationship(
        back_populates="analise",
        cascade="all, delete-orphan",
        order_by="SugestaoIA.id",
    )


class SugestaoIA(Base):
    __tablename__ = "sugestoes_ia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analise_id: Mapped[int] = mapped_column(ForeignKey("analises_ia.id"), nullable=False, index=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    analise: Mapped[AnaliseIA] = relationship(back_populates="sugestoes")
    decisoes: Mapped[list["DecisaoIA"]] = relationship(
        back_populates="sugestao",
        cascade="all, delete-orphan",
        order_by="DecisaoIA.id",
    )


class DecisaoIA(Base):
    __tablename__ = "decisoes_ia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sugestao_id: Mapped[int] = mapped_column(ForeignKey("sugestoes_ia.id"), nullable=False, index=True)
    decisao: Mapped[str] = mapped_column(String(20), nullable=False)
    decidido_por: Mapped[str] = mapped_column(String(80), nullable=False)
    decidido_em: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    mensagem_id: Mapped[int | None] = mapped_column(ForeignKey("mensagens.id"), nullable=True)
    texto_enviado: Mapped[str | None] = mapped_column(Text, nullable=True)

    sugestao: Mapped[SugestaoIA] = relationship(back_populates="decisoes")
