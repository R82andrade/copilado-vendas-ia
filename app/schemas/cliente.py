from datetime import date

from pydantic import BaseModel, ConfigDict


class ClienteCreate(BaseModel):
    nome: str
    cpf: str | None = None
    telefone: str | None = None
    email: str | None = None


class ClienteResponse(ClienteCreate):
    id: int
    data_cadastro: date

    model_config = ConfigDict(from_attributes=True)
