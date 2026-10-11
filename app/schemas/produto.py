from pydantic import BaseModel, ConfigDict, Field


class ProdutoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    marca: str = Field(..., min_length=2, max_length=100)
    categoria: str = Field(..., min_length=2, max_length=100)
    preco: float = Field(..., gt=0)
    estoque: int = Field(..., ge=0)
    desconto_maximo: float = Field(..., ge=0, le=100)


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoResponse(ProdutoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
