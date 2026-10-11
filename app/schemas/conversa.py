from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MensagemCreate(BaseModel):
    remetente: str
    texto: str


class MensagemResponse(MensagemCreate):
    id: int
    conversa_id: int
    data_envio: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversaCreate(BaseModel):
    cliente_id: int
    assunto: str = "Atendimento"
    status: str = "aberta"
    canal: str = "chat"


class ConversaStatusUpdate(BaseModel):
    status: str


class ConversaResponse(ConversaCreate):
    id: int
    data_criacao: datetime
    ultima_atualizacao: datetime
    mensagens: list[MensagemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
