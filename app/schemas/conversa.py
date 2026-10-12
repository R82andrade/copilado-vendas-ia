from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MensagemCreate(BaseModel):
    remetente: str
    texto: str = Field(min_length=1, max_length=4000)
    sugestao_id: int | None = Field(default=None, gt=0)

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A mensagem não pode estar vazia.")
        return value


class MensagemResponse(MensagemCreate):
    id: int
    conversa_id: int
    data_envio: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversaCreate(BaseModel):
    cliente_id: int
    assunto: str = "Atendimento"
    status: Literal["aberta", "pendente", "em_atendimento", "finalizada"] = "aberta"
    resultado: Literal["sem_resultado", "aguardando_retorno", "venda_realizada"] = "sem_resultado"
    canal: str = "chat"


class ConversaStatusUpdate(BaseModel):
    status: Literal["aberta", "pendente", "em_atendimento", "finalizada"]


class ConversaResultadoUpdate(BaseModel):
    resultado: Literal["sem_resultado", "aguardando_retorno", "venda_realizada"]


class ConversaResponsavelUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=80)


class ConversaResponse(ConversaCreate):
    id: int
    data_criacao: datetime
    ultima_atualizacao: datetime
    mensagens: list[MensagemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ConversaResumo(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: str
    assunto: str
    status: str
    resultado: str
    canal: str
    data_criacao: datetime
    ultima_atualizacao: datetime
    responsavel: str | None
    ultima_mensagem: str | None
    ultima_mensagem_em: datetime | None
    aguardando_resposta: bool
    sla_atrasada: bool


class ConversaPagina(BaseModel):
    items: list[ConversaResumo]
    total: int
    limit: int
    offset: int
    sla_minutes: int


class MensagemPagina(BaseModel):
    items: list[MensagemResponse]
    has_more: bool
    next_before_id: int | None
