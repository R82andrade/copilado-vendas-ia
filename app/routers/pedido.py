from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.configuracao_financeira import ConfiguracaoFinanceira
from app.models.pedido import ItemPedido, Pedido
from app.models.produto import Produto
from app.schemas.pedido import PedidoCreate, PedidoResponse
from app.services.financeiro import InvalidFinancialInputError
from app.services.financeiro_produto import calculate_product_finance


router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos"],
    dependencies=[Depends(require_auth)],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_pedido(
    pedido: PedidoCreate,
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == pedido.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )

    novo_pedido = Pedido(
        cliente_id=pedido.cliente_id,
        data_pedido=date.today(),
        total=0.0,
    )
    db.add(novo_pedido)
    db.flush()

    total_pedido = 0.0

    for item in pedido.itens:
        produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto {item.produto_id} não encontrado",
            )

        if item.desconto > produto.desconto_maximo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Desconto de {item.desconto}% excede o máximo permitido "
                    f"para {produto.nome} ({produto.desconto_maximo}%)"
                ),
            )

        if item.desconto > 0:
            config = db.query(ConfiguracaoFinanceira).filter(ConfiguracaoFinanceira.id == 1).first()
            try:
                financial = calculate_product_finance(
                    produto, config, discount_percent=Decimal(str(item.desconto))
                )
            except InvalidFinancialInputError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if financial["situacao"] == "dados_insuficientes":
                raise HTTPException(
                    status_code=422,
                    detail="Desconto não pode ser validado; dados financeiros ausentes: "
                    + ", ".join(financial["dados_ausentes"]),
                )
            if financial["situacao"] == "bloqueada":
                raise HTTPException(
                    status_code=400,
                    detail=f"Desconto bloqueado para {produto.nome}: {financial['motivo']}",
                )

        subtotal = round(
            item.quantidade * produto.preco * (1 - (item.desconto / 100)),
            2,
        )
        total_pedido += subtotal

        novo_item = ItemPedido(
            pedido_id=novo_pedido.id,
            produto_id=produto.id,
            quantidade=item.quantidade,
            preco_unitario=round(produto.preco, 2),
            desconto_aplicado=round(item.desconto, 2),
            subtotal=subtotal,
        )
        db.add(novo_item)

    novo_pedido.total = round(total_pedido, 2)
    db.commit()
    db.refresh(novo_pedido)

    return novo_pedido


@router.get("/", response_model=list[PedidoResponse])
def listar_pedidos(
    db: Session = Depends(get_db),
):
    return db.query(Pedido).all()
