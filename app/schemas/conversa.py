from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class ConversaResponse(ConversaCreate):
    id: int
    data_criacao: datetime
    ultima_atualizacao: datetime
    mensagens: list[MensagemResponse] = []

    model_config = ConfigDict(from_attributes=True)
