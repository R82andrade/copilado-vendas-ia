from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.mensagem import Mensagem
from app.schemas.conversa import (
    ConversaCreate,
    ConversaResponse,
    MensagemCreate,
    MensagemResponse,
)


router = APIRouter(
    prefix="/conversas",
    tags=["Conversas"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _buscar_conversa_por_id(db: Session, conversa_id: int):
    return db.query(Conversa).filter(Conversa.id == conversa_id).first()


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
        canal=conversa.canal,
    )

    db.add(nova_conversa)
    db.commit()
    db.refresh(nova_conversa)

    return nova_conversa


@router.get("/", response_model=list[ConversaResponse])
def listar_conversas(
    db: Session = Depends(get_db),
):
    return db.query(Conversa).order_by(Conversa.data_criacao.desc()).all()


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


@router.post(
    "/{conversa_id}/mensagens/",
    response_model=MensagemResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_mensagem(
    conversa_id: int,
    mensagem: MensagemCreate,
    db: Session = Depends(get_db),
):
    conversa = _buscar_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    nova_mensagem = Mensagem(
        conversa_id=conversa_id,
        remetente=mensagem.remetente,
        texto=mensagem.texto,
    )

    db.add(nova_mensagem)
    db.commit()
    db.refresh(nova_mensagem)

    return nova_mensagem


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
