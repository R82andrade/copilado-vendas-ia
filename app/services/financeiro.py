"""Cálculos financeiros unitários para apoiar decisões comerciais.

Fórmulas (percentuais são recebidos como números de 0 a 100):

* Lucro bruto simplificado = preço de venda - custo de aquisição.
* Margem bruta (%) = lucro bruto / preço de venda * 100. Não inclui outros custos.
* Contribuição = preço - aquisição - outros custos unitários - preço * (imposto + comissão) / 100.
* Margem de contribuição (%) = contribuição / preço * 100.
* Preço mínimo = (aquisição + outros custos) /
  (1 - (imposto + comissão + margem mínima) / 100).
* Desconto financeiro máximo (%) = (preço atual - preço mínimo) / preço atual * 100.

Margem é a parcela do preço que resta como lucro/contribuição; markup é o
acréscimo aplicado sobre o custo. Não são a mesma proporção. Custos fixos,
rateios, frete de venda e outras despesas só entram se forem fornecidos como
custos variáveis unitários ou percentuais apropriados. Estes cálculos não
representam lucro líquido.

Dados financeiros ausentes nunca são tratados como custo zero. Valores
monetários de saída são arredondados para centavos; o preço mínimo é sempre
arredondado para cima para não ficar abaixo da margem alvo.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP
from typing import TypeAlias


Number: TypeAlias = Decimal | int | str | float
CENT = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0")


class FinancialDataMissingError(ValueError):
    """Indica que faltam dados necessários para um cálculo financeiro."""


class InvalidFinancialInputError(ValueError):
    """Indica uma entrada financeira inválida ou uma combinação impossível."""


class DiscountNotAllowedError(ValueError):
    """Indica que a proposta viola o limite financeiro ou comercial."""


def _decimal(value: Number, field: str, *, required: bool = True) -> Decimal | None:
    if value is None:
        if required:
            raise FinancialDataMissingError(f"Dado financeiro ausente: {field}.")
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise InvalidFinancialInputError(f"Valor inválido para {field}.") from None
    if not result.is_finite():
        raise InvalidFinancialInputError(f"Valor inválido para {field}.")
    return result


def _money(value: Number, field: str, *, positive: bool = False) -> Decimal:
    result = _decimal(value, field)
    assert result is not None
    if result < ZERO or (positive and result == ZERO):
        qualifier = "maior que zero" if positive else "não negativo"
        raise InvalidFinancialInputError(f"{field} deve ser {qualifier}.")
    return result


def _percent(value: Number, field: str, *, allow_100: bool = True) -> Decimal:
    result = _decimal(value, field)
    assert result is not None
    if result < ZERO or result > HUNDRED or (not allow_100 and result == HUNDRED):
        upper = "menor que 100" if not allow_100 else "entre 0 e 100"
        raise InvalidFinancialInputError(f"{field} deve estar {upper}%.")
    return result


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def gross_profit_unit(sale_price: Number, acquisition_cost: Number) -> Decimal:
    """Retorna preço menos custo de aquisição; não desconta outros encargos."""
    price = _money(sale_price, "preço de venda", positive=True)
    cost = _money(acquisition_cost, "custo de aquisição")
    return _round_money(price - cost)


def gross_margin_percent(sale_price: Number, acquisition_cost: Number) -> Decimal:
    """Retorna a margem bruta percentual, ou seja, lucro bruto dividido pelo preço."""
    price = _money(sale_price, "preço de venda", positive=True)
    cost = _money(acquisition_cost, "custo de aquisição")
    return ((price - cost) / price * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)


def contribution_profit_unit(
    sale_price: Number,
    acquisition_cost: Number,
    other_variable_cost: Number,
    tax_percent: Number,
    commission_percent: Number,
) -> Decimal:
    """Calcula contribuição após custos unitários, impostos e comissão variáveis."""
    price = _money(sale_price, "preço de venda", positive=True)
    acquisition = _money(acquisition_cost, "custo de aquisição")
    other = _money(other_variable_cost, "outros custos variáveis")
    tax = _percent(tax_percent, "imposto")
    commission = _percent(commission_percent, "comissão")
    variable_rate = tax + commission
    if variable_rate >= HUNDRED:
        raise InvalidFinancialInputError("Impostos e comissão somados devem ser menores que 100%.")
    tax_amount = _round_money(price * tax / HUNDRED)
    commission_amount = _round_money(price * commission / HUNDRED)
    return _round_money(price - acquisition - other - tax_amount - commission_amount)


def contribution_margin_percent(
    sale_price: Number,
    acquisition_cost: Number,
    other_variable_cost: Number,
    tax_percent: Number,
    commission_percent: Number,
) -> Decimal:
    """Retorna a contribuição estimada como percentual do preço efetivo de venda."""
    price = _money(sale_price, "preço de venda", positive=True)
    contribution = contribution_profit_unit(
        price, acquisition_cost, other_variable_cost, tax_percent, commission_percent
    )
    return (contribution / price * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)


def minimum_sale_price(
    acquisition_cost: Number,
    other_variable_cost: Number,
    tax_percent: Number,
    commission_percent: Number,
    minimum_contribution_margin_percent: Number,
) -> Decimal:
    """Calcula o menor preço que atinge a margem alvo, arredondado para cima.

    O denominador precisa ser positivo: soma de impostos, comissão e margem
    mínima deve ser menor que 100%. Custos ausentes devem ser passados como
    ``None`` e geram ``FinancialDataMissingError``; zero deve ser informado
    explicitamente quando for um valor conhecido.
    """
    acquisition = _money(acquisition_cost, "custo de aquisição")
    other = _money(other_variable_cost, "outros custos variáveis")
    tax = _percent(tax_percent, "imposto")
    commission = _percent(commission_percent, "comissão")
    target = _percent(minimum_contribution_margin_percent, "margem mínima", allow_100=False)
    rate_sum = tax + commission + target
    if rate_sum >= HUNDRED:
        raise InvalidFinancialInputError(
            "Impostos, comissão e margem mínima somados devem ser menores que 100%."
        )
    raw_price = (acquisition + other) / (Decimal("1") - rate_sum / HUNDRED)
    candidate = raw_price.quantize(CENT, rounding=ROUND_CEILING)
    # Percentuais são cobrados em centavos individualmente. Corrige eventual
    # diferença de um centavo causada pelo arredondamento de imposto/comissão.
    while candidate > ZERO and (
        contribution_profit_unit(candidate, acquisition, other, tax, commission)
        / candidate * HUNDRED
    ) < target:
        candidate += CENT
    return candidate


def maximum_discount_percent(sale_price: Number, minimum_price: Number) -> Decimal:
    """Calcula o limite financeiro de desconto; não considera a política comercial."""
    price = _money(sale_price, "preço de venda", positive=True)
    floor = _money(minimum_price, "preço mínimo")
    if floor >= price:
        return ZERO.quantize(CENT)
    raw_discount = (price - floor) / price * HUNDRED
    # O arredondamento para baixo impede que os centésimos extrapolem o preço mínimo.
    return raw_discount.quantize(CENT, rounding=ROUND_DOWN)


def permitted_discount_percent(
    sale_price: Number,
    minimum_price: Number,
    commercial_discount_limit: Number | None,
) -> Decimal | None:
    """Combina limites financeiro e comercial; ``None`` significa política ausente."""
    if commercial_discount_limit is None:
        # Ainda valida os dados e calcula o limite financeiro sem inventar política.
        maximum_discount_percent(sale_price, minimum_price)
        return None
    commercial = _percent(commercial_discount_limit, "limite comercial de desconto")
    return min(maximum_discount_percent(sale_price, minimum_price), commercial)


def discounted_price(sale_price: Number, discount_percent: Number) -> Decimal:
    """Calcula o preço após desconto percentual e arredonda para centavos."""
    price = _money(sale_price, "preço de venda", positive=True)
    discount = _percent(discount_percent, "desconto")
    return _round_money(price * (HUNDRED - discount) / HUNDRED)


def percentage_amount(base_amount: Number, percent: Number) -> Decimal:
    """Calcula um encargo percentual sobre a venda e arredonda em centavos."""
    base = _money(base_amount, "base do percentual")
    rate = _percent(percent, "percentual")
    return _round_money(base * rate / HUNDRED)


@dataclass(frozen=True)
class DiscountSimulation:
    original_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    maximum_allowed_percent: Decimal | None
    allowed: bool


def simulate_discount(
    sale_price: Number,
    discount_percent: Number,
    minimum_price: Number,
    commercial_discount_limit: Number | None,
) -> DiscountSimulation:
    """Simula e valida desconto contra os limites financeiro e comercial.

    Se o limite comercial não foi informado, a simulação é calculada, mas não
    pode ser declarada autorizada. A aprovação de exceções é outro fluxo.
    """
    price = _money(sale_price, "preço de venda", positive=True)
    discount = _percent(discount_percent, "desconto")
    floor = _money(minimum_price, "preço mínimo")
    maximum = permitted_discount_percent(price, floor, commercial_discount_limit)
    final = discounted_price(price, discount)
    allowed = maximum is not None and discount <= maximum and final >= floor
    return DiscountSimulation(
        original_price=_round_money(price),
        discount_amount=_round_money(price - final),
        final_price=final,
        maximum_allowed_percent=maximum,
        allowed=allowed,
    )


def validate_discount(
    sale_price: Number,
    discount_percent: Number,
    minimum_price: Number,
    commercial_discount_limit: Number | None,
) -> DiscountSimulation:
    """Simula desconto e lança erro se exceder qualquer regra ou faltar política."""
    result = simulate_discount(sale_price, discount_percent, minimum_price, commercial_discount_limit)
    if result.maximum_allowed_percent is None:
        raise FinancialDataMissingError("Limite comercial de desconto não informado.")
    if not result.allowed:
        raise DiscountNotAllowedError(
            f"Desconto não permitido: máximo de {result.maximum_allowed_percent}% pela política vigente."
        )
    return result
