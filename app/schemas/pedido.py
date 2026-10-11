from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ItemPedidoCreate(BaseModel):
    produto_id: int = Field(..., gt=0)
    quantidade: int = Field(..., gt=0)
    desconto: float = Field(default=0.0, ge=0, le=100)


class PedidoCreate(BaseModel):
    cliente_id: int = Field(..., gt=0)
    itens: list[ItemPedidoCreate] = Field(..., min_length=1)


class ItemPedidoResponse(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: float
    desconto_aplicado: float
    subtotal: float

    model_config = ConfigDict(from_attributes=True)


class PedidoResponse(BaseModel):
    id: int
    cliente_id: int
    data_pedido: date
    total: float
    itens: list[ItemPedidoResponse]

    model_config = ConfigDict(from_attributes=True)
