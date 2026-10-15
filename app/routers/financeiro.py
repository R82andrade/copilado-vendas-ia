from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import SessionLocal
from app.models.configuracao_financeira import ConfiguracaoFinanceira
from app.models.produto import Produto
from app.schemas.financeiro import DiscountSimulationRequest, FinanceConfigUpdate, FinanceProductUpdate
from app.services.financeiro import InvalidFinancialInputError
from app.services.financeiro_produto import calculate_product_finance


router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def financial_user(user: dict = Depends(require_auth)):
    if user["role"] not in {"admin", "vendas"}:
        raise HTTPException(status_code=403, detail="Seu perfil não pode consultar dados financeiros.")
    return user


def administrator(user: dict = Depends(require_auth)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Somente administradores podem alterar configurações financeiras.")
    return user


def get_product(db: Session, product_id: int) -> Produto:
    product = db.query(Produto).filter(Produto.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return product


def get_config(db: Session):
    return db.query(ConfiguracaoFinanceira).filter(ConfiguracaoFinanceira.id == 1).first()


def _calculate(product: Produto, config, discount: Decimal):
    try:
        return calculate_product_finance(product, config, discount_percent=discount)
    except InvalidFinancialInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/configuracao")
def consultar_configuracao(
    _: dict = Depends(administrator),
    db: Session = Depends(get_db),
):
    config = get_config(db)
    if not config:
        return {"configurada": False, "dados_ausentes": [
            "imposto_variavel_percentual", "comissao_percentual",
            "margem_contribuicao_minima", "limite_desconto_comercial",
        ]}
    return {
        "configurada": True,
        "imposto_variavel_percentual": config.imposto_variavel_percentual,
        "comissao_percentual": config.comissao_percentual,
        "margem_contribuicao_minima": config.margem_contribuicao_minima,
        "limite_desconto_comercial": config.limite_desconto_comercial,
        "responsavel_username": config.responsavel_username,
    }


@router.put("/configuracao")
def atualizar_configuracao(
    payload: FinanceConfigUpdate,
    user: dict = Depends(administrator),
    db: Session = Depends(get_db),
):
    if payload.imposto_variavel_percentual is not None and payload.comissao_percentual is not None:
        product_margins = db.query(Produto.margem_contribuicao_minima).filter(
            Produto.margem_contribuicao_minima.isnot(None)
        ).all()
        if any(
            payload.imposto_variavel_percentual + payload.comissao_percentual + margin >= Decimal("100")
            for (margin,) in product_margins
        ):
            raise HTTPException(
                status_code=422,
                detail="A política global seria incompatível com a margem mínima de um ou mais produtos.",
            )
    config = get_config(db)
    if config is None:
        config = ConfiguracaoFinanceira(id=1)
        db.add(config)
    for field, value in payload.model_dump().items():
        setattr(config, field, value)
    config.responsavel_username = user["username"]
    db.commit()
    db.refresh(config)
    return {
        "configurada": True,
        "imposto_variavel_percentual": config.imposto_variavel_percentual,
        "comissao_percentual": config.comissao_percentual,
        "margem_contribuicao_minima": config.margem_contribuicao_minima,
        "limite_desconto_comercial": config.limite_desconto_comercial,
        "responsavel_username": config.responsavel_username,
    }


@router.get("/produtos/{produto_id}")
def consultar_financeiro_produto(
    produto_id: int,
    _: dict = Depends(financial_user),
    db: Session = Depends(get_db),
):
    return _calculate(get_product(db, produto_id), get_config(db), Decimal("0"))


@router.put("/produtos/{produto_id}")
def atualizar_financeiro_produto(
    produto_id: int,
    payload: FinanceProductUpdate,
    _: dict = Depends(administrator),
    db: Session = Depends(get_db),
):
    product = get_product(db, produto_id)
    config = get_config(db)
    effective_margin = payload.margem_contribuicao_minima
    if effective_margin is None:
        effective_margin = config.margem_contribuicao_minima if config else None
    if config and all(value is not None for value in (
        config.imposto_variavel_percentual, config.comissao_percentual, effective_margin
    )) and (
        config.imposto_variavel_percentual + config.comissao_percentual + effective_margin >= Decimal("100")
    ):
        raise HTTPException(
            status_code=422,
            detail="Impostos, comissão e margem mínima somados devem ser menores que 100%.",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return {
        "produto_id": product.id,
        "custo_aquisicao": product.custo_aquisicao,
        "outros_custos_variaveis": product.outros_custos_variaveis,
        "margem_contribuicao_minima": product.margem_contribuicao_minima,
        "limite_desconto_comercial": product.limite_desconto_comercial,
    }


@router.post("/produtos/{produto_id}/simulacoes")
def simular_desconto(
    produto_id: int,
    payload: DiscountSimulationRequest,
    _: dict = Depends(financial_user),
    db: Session = Depends(get_db),
):
    product = get_product(db, produto_id)
    discount = payload.desconto_percentual
    if payload.preco_final_pretendido is not None:
        price = Decimal(str(product.preco))
        if price <= 0:
            raise HTTPException(status_code=422, detail="Preço cadastrado deve ser maior que zero.")
        if payload.preco_final_pretendido > price:
            raise HTTPException(status_code=422, detail="O preço final pretendido não pode superar o preço cadastrado.")
        discount = (price - payload.preco_final_pretendido) / price * Decimal("100")
    result = _calculate(product, get_config(db), discount)
    return result
