"""Adapta os dados persistidos aos cálculos puros de ``financeiro``."""

from decimal import Decimal

from app.models.configuracao_financeira import ConfiguracaoFinanceira
from app.models.produto import Produto
from app.services.financeiro import (
    InvalidFinancialInputError,
    contribution_margin_percent,
    contribution_profit_unit,
    discounted_price,
    gross_margin_percent,
    gross_profit_unit,
    maximum_discount_percent,
    minimum_sale_price,
    permitted_discount_percent,
    percentage_amount,
    simulate_discount,
)


def calculate_product_finance(
    product: Produto,
    config: ConfiguracaoFinanceira | None,
    *,
    discount_percent: Decimal = Decimal("0"),
) -> dict:
    """Resolve precedência produto/loja e devolve análise ou dados insuficientes."""
    def resolve(product_value, config_value):
        return product_value if product_value is not None else config_value

    tax = config.imposto_variavel_percentual if config else None
    commission = config.comissao_percentual if config else None
    min_margin = resolve(
        product.margem_contribuicao_minima,
        config.margem_contribuicao_minima if config else None,
    )
    configured_commercial_limit = resolve(
        product.limite_desconto_comercial,
        config.limite_desconto_comercial if config else None,
    )
    # The legacy catalog limit remains a hard ceiling for backwards compatibility.
    legacy_catalog_limit = Decimal(str(product.desconto_maximo))
    commercial_limit = min(
        configured_commercial_limit if configured_commercial_limit is not None else legacy_catalog_limit,
        legacy_catalog_limit,
    )
    acquisition = product.custo_aquisicao
    other_cost = product.outros_custos_variaveis
    missing = [
        name for name, value in (
            ("custo_aquisicao", acquisition),
            ("outros_custos_variaveis", other_cost),
            ("imposto_variavel_percentual", tax),
            ("comissao_percentual", commission),
            ("margem_contribuicao_minima", min_margin),
        ) if value is None
    ]
    price = Decimal(str(product.preco))
    if not price.is_finite() or price <= 0:
        raise InvalidFinancialInputError("Preço cadastrado deve ser maior que zero.")
    discount_percent = Decimal(str(discount_percent))
    if missing:
        return {
            "produto_id": product.id,
            "situacao": "dados_insuficientes",
            "dados_ausentes": missing,
            "preco_original": price,
            "desconto_percentual": discount_percent,
            "dados_financeiros": {
                "custo_aquisicao": acquisition,
                "outros_custos_variaveis": other_cost,
                "imposto_variavel_percentual": config.imposto_variavel_percentual if config else None,
                "comissao_percentual": config.comissao_percentual if config else None,
                "margem_contribuicao_minima": product.margem_contribuicao_minima,
                "limite_desconto_comercial": product.limite_desconto_comercial,
                "limite_catalogo_existente": legacy_catalog_limit,
            },
            "parametros_efetivos": {
                "imposto_variavel_percentual": tax,
                "comissao_percentual": commission,
                "margem_contribuicao_minima": min_margin,
                "limite_desconto_comercial": commercial_limit,
            },
        }

    minimum_price = minimum_sale_price(acquisition, other_cost, tax, commission, min_margin)
    final_price = discounted_price(price, discount_percent)
    simulation = simulate_discount(price, discount_percent, minimum_price, commercial_limit)
    return {
        "produto_id": product.id,
        "situacao": "permitida" if simulation.allowed else "bloqueada",
        "dados_ausentes": [],
        "dados_financeiros": {
            "custo_aquisicao": acquisition,
            "outros_custos_variaveis": other_cost,
            "imposto_variavel_percentual": config.imposto_variavel_percentual if config else None,
            "comissao_percentual": config.comissao_percentual if config else None,
            "margem_contribuicao_minima": product.margem_contribuicao_minima,
            "limite_desconto_comercial": product.limite_desconto_comercial,
            "limite_catalogo_existente": legacy_catalog_limit,
        },
        "parametros_efetivos": {
            "imposto_variavel_percentual": tax,
            "comissao_percentual": commission,
            "margem_contribuicao_minima": min_margin,
            "limite_desconto_comercial": commercial_limit,
        },
        "preco_original": price,
        "desconto_percentual": discount_percent,
        "valor_desconto": simulation.discount_amount,
        "preco_final": final_price,
        "custo_aquisicao": acquisition,
        "outros_custos_variaveis": other_cost,
        "imposto_variavel_percentual": tax,
        "imposto_variavel_valor": percentage_amount(final_price, tax),
        "comissao_percentual": commission,
        "comissao_valor": percentage_amount(final_price, commission),
        "lucro_bruto": gross_profit_unit(final_price, acquisition),
        "margem_bruta_percentual": gross_margin_percent(final_price, acquisition),
        "contribuicao_unitaria": contribution_profit_unit(
            final_price, acquisition, other_cost, tax, commission
        ),
        "margem_contribuicao_percentual": contribution_margin_percent(
            final_price, acquisition, other_cost, tax, commission
        ),
        "preco_minimo": minimum_price,
        "limite_financeiro_desconto_percentual": maximum_discount_percent(price, minimum_price),
        "limite_comercial_desconto_percentual": commercial_limit,
        "limite_comercial_configurado_percentual": configured_commercial_limit,
        "limite_permitido_desconto_percentual": permitted_discount_percent(
            price, minimum_price, commercial_limit
        ),
        "motivo": None if simulation.allowed else (
            "O preço final ficou abaixo do preço mínimo financeiro."
            if final_price < minimum_price
            else "O desconto ultrapassa o limite comercial configurado."
        ),
    }
