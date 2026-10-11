from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.produto import Produto
from app.schemas.produto import ProdutoCreate, ProdutoResponse


router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _buscar_produto_por_id(db: Session, produto_id: int):
    return db.query(Produto).filter(Produto.id == produto_id).first()


@router.post(
    "/",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_produto(
    produto: ProdutoCreate,
    db: Session = Depends(get_db),
):
    novo_produto = Produto(
        nome=produto.nome,
        marca=produto.marca,
        categoria=produto.categoria,
        preco=produto.preco,
        estoque=produto.estoque,
        desconto_maximo=produto.desconto_maximo,
    )

    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)

    return novo_produto


@router.get("/", response_model=list[ProdutoResponse])
def listar_produtos(
    db: Session = Depends(get_db),
):
    return db.query(Produto).all()


@router.get("/{produto_id}", response_model=ProdutoResponse)
def buscar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
):
    produto = _buscar_produto_por_id(db, produto_id)
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )

    return produto


@router.put("/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(
    produto_id: int,
    produto: ProdutoCreate,
    db: Session = Depends(get_db),
):
    produto_db = _buscar_produto_por_id(db, produto_id)
    if not produto_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )

    produto_db.nome = produto.nome
    produto_db.marca = produto.marca
    produto_db.categoria = produto.categoria
    produto_db.preco = produto.preco
    produto_db.estoque = produto.estoque
    produto_db.desconto_maximo = produto.desconto_maximo

    db.commit()
    db.refresh(produto_db)

    return produto_db


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_produto(
    produto_id: int,
    db: Session = Depends(get_db),
):
    produto = _buscar_produto_por_id(db, produto_id)
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )

    db.delete(produto)
    db.commit()

    return None
