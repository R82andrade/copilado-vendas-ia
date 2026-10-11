from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Mensagem(Base):
    __tablename__ = "mensagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id"), nullable=False)
    remetente: Mapped[str] = mapped_column(String(50), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    data_envio: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversa: Mapped["Conversa"] = relationship(back_populates="mensagens")
