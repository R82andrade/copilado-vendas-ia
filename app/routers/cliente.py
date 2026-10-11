from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteResponse


router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _buscar_cliente_por_id(db: Session, cliente_id: int):
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


@router.post(
    "/",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED
)
def criar_cliente(
    cliente: ClienteCreate,
    db: Session = Depends(get_db)
):
    if cliente.cpf:
        cliente_existente = (
            db.query(Cliente)
            .filter(Cliente.cpf == cliente.cpf)
            .first()
        )

        if cliente_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPF já cadastrado",
            )

    novo_cliente = Cliente(
        nome=cliente.nome,
        cpf=cliente.cpf,
        telefone=cliente.telefone,
        email=cliente.email,
        data_cadastro=date.today()
    )

    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)

    return novo_cliente


@router.get("/", response_model=list[ClienteResponse])
def listar_clientes(
    db: Session = Depends(get_db),
):
    return db.query(Cliente).all()


@router.get("/{cliente_id}", response_model=ClienteResponse)
def buscar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    cliente = _buscar_cliente_por_id(db, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )

    return cliente


@router.put("/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(
    cliente_id: int,
    cliente: ClienteCreate,
    db: Session = Depends(get_db),
):
    cliente_db = _buscar_cliente_por_id(db, cliente_id)
    if not cliente_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )

    if cliente.cpf and cliente.cpf != cliente_db.cpf:
        existente = (
            db.query(Cliente)
            .filter(Cliente.cpf == cliente.cpf)
            .first()
        )
        if existente and existente.id != cliente_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPF já cadastrado",
            )

    cliente_db.nome = cliente.nome
    cliente_db.cpf = cliente.cpf
    cliente_db.telefone = cliente.telefone
    cliente_db.email = cliente.email

    db.commit()
    db.refresh(cliente_db)

    return cliente_db


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    cliente = _buscar_cliente_por_id(db, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )

    db.delete(cliente)
    db.commit()

    return None
