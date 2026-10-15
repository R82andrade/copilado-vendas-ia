from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConfiguracaoFinanceira(Base):
    """Parâmetros financeiros globais da loja (linha única, id=1)."""

    __tablename__ = "configuracoes_financeiras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    imposto_variavel_percentual: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    comissao_percentual: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    margem_contribuicao_minima: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    limite_desconto_comercial: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    responsavel_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
