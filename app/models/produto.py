from decimal import Decimal

from sqlalchemy import Float, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    marca: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    preco: Mapped[float] = mapped_column(Float, nullable=False)
    estoque: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    desconto_maximo: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    custo_aquisicao: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    outros_custos_variaveis: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    margem_contribuicao_minima: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    limite_desconto_comercial: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    itens_pedido: Mapped[list["ItemPedido"]] = relationship(back_populates="produto")
