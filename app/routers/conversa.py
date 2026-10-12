from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.conversa_canal import ConversaResponsavel, MensagemCanal
from app.models.ia import DecisaoIA, SugestaoIA
from app.models.mensagem import Mensagem
from app.models.usuario import Usuario
from app.schemas.conversa import (
    ConversaCreate,
    ConversaPagina,
    ConversaResponsavelUpdate,
    ConversaResultadoUpdate,
    ConversaResponse,
    ConversaStatusUpdate,
    MensagemCreate,
    MensagemPagina,
    MensagemResponse,
)
from app.whatsapp import WhatsAppSendError, send_whatsapp_text


SLA_MINUTES = 15
STATUS_TRANSITIONS = {
    "aberta": {"pendente", "em_atendimento", "finalizada"},
    "pendente": {"aberta", "em_atendimento", "finalizada"},
    "em_atendimento": {"aberta", "pendente", "finalizada"},
    "finalizada": {"aberta"},
}

router = APIRouter(
    prefix="/conversas",
    tags=["Conversas"],
    dependencies=[Depends(require_auth)],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _buscar_conversa_por_id(db: Session, conversa_id: int):
    return db.query(Conversa).filter(Conversa.id == conversa_id).first()


def _normalize_phone(phone: str | None) -> str:
    return "".join(character for character in (phone or "") if character.isdigit())


@router.post(
    "/",
    response_model=ConversaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_conversa(
    conversa: ConversaCreate,
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == conversa.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )

    nova_conversa = Conversa(
        cliente_id=conversa.cliente_id,
        assunto=conversa.assunto,
        status=conversa.status,
        resultado=conversa.resultado,
        canal=conversa.canal,
    )

    db.add(nova_conversa)
    db.commit()
    db.refresh(nova_conversa)

    return nova_conversa


@router.get("/", response_model=list[ConversaResponse])
def listar_conversas(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    canal: str | None = None,
    cliente_id: int | None = None,
):
    query = db.query(Conversa)

    if status_filter:
        query = query.filter(Conversa.status == status_filter)
    if canal:
        query = query.filter(Conversa.canal == canal)
    if cliente_id is not None:
        query = query.filter(Conversa.cliente_id == cliente_id)

    return query.order_by(Conversa.ultima_atualizacao.desc()).all()


@router.get("/pagina", response_model=ConversaPagina)
def listar_conversas_paginadas(
    db: Session = Depends(get_db),
    query_text: str | None = Query(default=None, max_length=150, alias="q"),
    status_filter: str | None = Query(default=None, alias="status"),
    canal: str | None = Query(default=None, max_length=50),
    responsavel: str | None = Query(default=None, max_length=80),
    desde: date | None = None,
    ate: date | None = None,
    atrasadas: bool = False,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    latest_message_text = (
        db.query(Mensagem.texto)
        .filter(Mensagem.conversa_id == Conversa.id)
        .order_by(Mensagem.id.desc())
        .limit(1)
        .correlate(Conversa)
        .scalar_subquery()
    )
    latest_message_at = (
        db.query(Mensagem.data_envio)
        .filter(Mensagem.conversa_id == Conversa.id)
        .order_by(Mensagem.id.desc())
        .limit(1)
        .correlate(Conversa)
        .scalar_subquery()
    )
    latest_customer_message = (
        db.query(func.max(Mensagem.data_envio))
        .filter(Mensagem.conversa_id == Conversa.id, Mensagem.remetente == "cliente")
        .correlate(Conversa)
        .scalar_subquery()
    )
    latest_agent_message = (
        db.query(func.max(Mensagem.data_envio))
        .filter(Mensagem.conversa_id == Conversa.id, Mensagem.remetente == "atendente")
        .correlate(Conversa)
        .scalar_subquery()
    )
    responsible_username = (
        db.query(ConversaResponsavel.username)
        .filter(ConversaResponsavel.conversa_id == Conversa.id)
        .correlate(Conversa)
        .scalar_subquery()
    )
    now = datetime.utcnow()
    awaiting_response = or_(
        latest_customer_message.isnot(None) & latest_agent_message.is_(None),
        latest_customer_message > latest_agent_message,
    )
    overdue = (
        (Conversa.status != "finalizada")
        & awaiting_response
        & (latest_customer_message <= now - timedelta(minutes=SLA_MINUTES))
    )
    query = db.query(
        Conversa,
        Cliente.nome.label("cliente_nome"),
        responsible_username.label("responsavel"),
        latest_customer_message.label("ultima_mensagem_cliente_em"),
        latest_agent_message.label("ultima_mensagem_atendente_em"),
        latest_message_text.label("ultima_mensagem"),
        latest_message_at.label("ultima_mensagem_em"),
    ).join(Cliente, Conversa.cliente_id == Cliente.id)
    if query_text:
        pattern = f"%{query_text.strip()}%"
        query = query.filter(or_(
            Cliente.nome.ilike(pattern),
            Conversa.assunto.ilike(pattern),
            Conversa.canal.ilike(pattern),
        ))
    if status_filter:
        query = query.filter(Conversa.status == status_filter)
    if canal:
        query = query.filter(Conversa.canal == canal)
    if responsavel == "sem_atribuicao":
        query = query.filter(responsible_username.is_(None))
    elif responsavel:
        query = query.filter(responsible_username == responsavel)
    if desde:
        query = query.filter(Conversa.data_criacao >= datetime.combine(desde, time.min))
    if ate:
        query = query.filter(Conversa.data_criacao < datetime.combine(ate + timedelta(days=1), time.min))
    if atrasadas:
        query = query.filter(overdue)

    total = query.count()
    rows = query.order_by(Conversa.ultima_atualizacao.desc(), Conversa.id.desc()).offset(offset).limit(limit).all()
    items = []
    for conversa, cliente_nome, responsavel, latest_customer, latest_agent, last_text, last_sent in rows:
        is_waiting = latest_customer is not None and (
            latest_agent is None or latest_customer > latest_agent
        )
        items.append({
            "id": conversa.id,
            "cliente_id": conversa.cliente_id,
            "cliente_nome": cliente_nome,
            "assunto": conversa.assunto,
            "status": conversa.status,
            "resultado": conversa.resultado,
            "canal": conversa.canal,
            "data_criacao": conversa.data_criacao,
            "ultima_atualizacao": conversa.ultima_atualizacao,
            "responsavel": responsavel,
            "ultima_mensagem": last_text,
            "ultima_mensagem_em": last_sent,
            "aguardando_resposta": is_waiting,
            "sla_atrasada": bool(is_waiting and latest_customer <= now - timedelta(minutes=SLA_MINUTES)),
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset, "sla_minutes": SLA_MINUTES}


@router.get("/{conversa_id}", response_model=ConversaResponse)
def buscar_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    return conversa


@router.patch("/{conversa_id}/status", response_model=ConversaResponse)
def atualizar_status_conversa(
    conversa_id: int,
    payload: ConversaStatusUpdate,
    db: Session = Depends(get_db),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    if payload.status != conversa.status and payload.status not in STATUS_TRANSITIONS.get(conversa.status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transição de status inválida: {conversa.status} para {payload.status}",
        )
    conversa.status = payload.status
    conversa.ultima_atualizacao = datetime.utcnow()

    db.commit()
    db.refresh(conversa)

    return conversa


@router.patch("/{conversa_id}/resultado", response_model=ConversaResponse)
def atualizar_resultado_conversa(
    conversa_id: int,
    payload: ConversaResultadoUpdate,
    db: Session = Depends(get_db),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    conversa.resultado = payload.resultado
    conversa.ultima_atualizacao = datetime.utcnow()
    db.commit()
    db.refresh(conversa)
    return conversa


@router.patch("/{conversa_id}/responsavel")
def atualizar_responsavel(
    conversa_id: int,
    payload: ConversaResponsavelUpdate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(require_auth),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    assignment = db.query(ConversaResponsavel).filter(
        ConversaResponsavel.conversa_id == conversa_id
    ).first()
    if payload.username is None:
        if assignment:
            db.delete(assignment)
    else:
        account = db.query(Usuario).filter(
            Usuario.username == payload.username,
            Usuario.ativo.is_(True),
            Usuario.role.in_(("admin", "atendimento")),
        ).first()
        if not account:
            raise HTTPException(status_code=422, detail="Selecione um atendente ativo")
        if assignment:
            assignment.username = account.username
            assignment.atribuido_por = usuario["username"]
            assignment.atribuido_em = datetime.utcnow()
        else:
            db.add(ConversaResponsavel(
                conversa_id=conversa_id,
                username=account.username,
                atribuido_por=usuario["username"],
            ))
    conversa.ultima_atualizacao = datetime.utcnow()
    db.commit()
    return {"conversa_id": conversa_id, "responsavel": payload.username}


@router.post(
    "/{conversa_id}/mensagens/",
    response_model=MensagemResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_mensagem(
    conversa_id: int,
    mensagem: MensagemCreate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(require_auth),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    if mensagem.remetente not in {"cliente", "atendente"}:
        raise HTTPException(status_code=422, detail="Remetente inválido")
    if mensagem.remetente == "cliente" and mensagem.sugestao_id is not None:
        raise HTTPException(status_code=422, detail="Mensagens de clientes não podem usar sugestão de resposta")

    sugestao = None
    if mensagem.sugestao_id is not None:
        sugestao = (
            db.query(SugestaoIA)
            .filter(
                SugestaoIA.id == mensagem.sugestao_id,
                SugestaoIA.conversa_id == conversa_id,
                SugestaoIA.tipo == "resposta",
            )
            .first()
        )
        if not sugestao or sugestao.status != "aceita":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A sugestão deve ser aceita antes de registrar o envio.",
            )

    nova_mensagem = Mensagem(
        conversa_id=conversa_id,
        remetente=mensagem.remetente,
        texto=mensagem.texto,
    )

    provider_message_id = None
    if conversa.canal == "whatsapp" and mensagem.remetente == "atendente":
        cliente = db.query(Cliente).filter(Cliente.id == conversa.cliente_id).first()
        if not cliente or not _normalize_phone(cliente.telefone):
            raise HTTPException(status_code=422, detail="O cliente não tem um telefone válido para WhatsApp")
        try:
            provider_message_id = send_whatsapp_text(cliente.telefone, mensagem.texto)
        except WhatsAppSendError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    conversa.ultima_atualizacao = datetime.utcnow()
    db.add(nova_mensagem)
    if provider_message_id:
        db.flush()
        db.add(MensagemCanal(
            mensagem_id=nova_mensagem.id,
            provider="whatsapp",
            provider_message_id=provider_message_id,
            direction="outbound",
        ))
    if sugestao:
        db.flush()
        sugestao.status = "enviada"
        sugestao.decisoes.append(
            DecisaoIA(
                decisao="enviada",
                decidido_por=usuario["username"],
                mensagem_id=nova_mensagem.id,
                texto_enviado=mensagem.texto,
            )
        )
    db.commit()
    db.refresh(nova_mensagem)

    return nova_mensagem


@router.get("/{conversa_id}/mensagens/pagina", response_model=MensagemPagina)
def listar_mensagens_paginadas(
    conversa_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    query = db.query(Mensagem).filter(Mensagem.conversa_id == conversa_id)
    if before_id is not None:
        query = query.filter(Mensagem.id < before_id)
    rows = query.order_by(Mensagem.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    page = list(reversed(rows[:limit]))
    return {
        "items": page,
        "has_more": has_more,
        "next_before_id": page[0].id if has_more and page else None,
    }


@router.get("/{conversa_id}/mensagens/", response_model=list[MensagemResponse])
def listar_mensagens(
    conversa_id: int,
    db: Session = Depends(get_db),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    return (
        db.query(Mensagem)
        .filter(Mensagem.conversa_id == conversa_id)
        .order_by(Mensagem.data_envio.asc())
        .all()
    )
