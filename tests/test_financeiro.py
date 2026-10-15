from decimal import Decimal

import pytest

from app.services.financeiro import (
    DiscountNotAllowedError,
    FinancialDataMissingError,
    InvalidFinancialInputError,
    contribution_margin_percent,
    contribution_profit_unit,
    discounted_price,
    gross_margin_percent,
    gross_profit_unit,
    maximum_discount_percent,
    minimum_sale_price,
    percentage_amount,
    permitted_discount_percent,
    simulate_discount,
    validate_discount,
)


D = Decimal


def test_lucro_bruto_e_margem_bruta():
    assert gross_profit_unit(D("200.00"), D("100.00")) == D("100.00")
    assert gross_margin_percent(D("200.00"), D("100.00")) == D("50.00")


def test_margem_bruta_pode_ser_negativa_quando_vende_abaixo_do_custo():
    assert gross_profit_unit("90.00", "100.00") == D("-10.00")
    assert gross_margin_percent("90.00", "100.00") == D("-11.11")


def test_contribuicao_considera_custos_unitarios_imposto_e_comissao():
    # R$ 200 - R$ 100 - R$ 10 - (13% de R$ 200) = R$ 64.
    assert contribution_profit_unit("200", "100", "10", "8", "5") == D("64.00")
    assert contribution_margin_percent("200", "100", "10", "8", "5") == D("32.00")


def test_preco_minimo_atinge_margem_alvo_e_arredonda_para_cima():
    # (100 + 10) / (1 - (8 + 5 + 20)/100) = 164,1791... -> R$ 164,18.
    assert minimum_sale_price("100", "10", "8", "5", "20") == D("164.18")
    assert minimum_sale_price("1", "0", "0", "0", "33.33") == D("1.50")


def test_desconto_maximo_financeiro_e_limite_comercial():
    assert maximum_discount_percent("200", "164.18") == D("17.91")
    assert permitted_discount_percent("200", "164.18", "15") == D("15")
    assert permitted_discount_percent("200", "164.18", None) is None
    assert maximum_discount_percent("100", "100") == D("0.00")


def test_preco_e_valor_apos_desconto_sao_arredondados_a_centavos():
    assert discounted_price("200", "10") == D("180.00")
    result = simulate_discount("200", "10", "164.18", "15")
    assert result.original_price == D("200.00")
    assert result.discount_amount == D("20.00")
    assert result.final_price == D("180.00")
    assert result.maximum_allowed_percent == D("15")
    assert result.allowed is True


def test_encargo_percentual_em_reais():
    assert percentage_amount("180", "8") == D("14.40")
    assert percentage_amount("180", "5") == D("9.00")


def test_preco_minimo_compensa_arredondamento_separado_dos_encargos():
    assert minimum_sale_price("0.03", "0", "10", "10", "30") == D("0.08")
    assert contribution_profit_unit("0.08", "0.03", "0", "10", "10") == D("0.03")


def test_simulacao_rejeita_excesso_comercial_e_preco_abaixo_do_minimo():
    assert simulate_discount("200", "16", "164.18", "15").allowed is False
    assert simulate_discount("200", "20", "164.18", "25").allowed is False
    with pytest.raises(DiscountNotAllowedError, match="máximo de 15%"):
        validate_discount("200", "16", "164.18", "15")


def test_sem_limite_comercial_nao_declara_desconto_autorizado():
    result = simulate_discount("200", "5", "164.18", None)
    assert result.maximum_allowed_percent is None
    assert result.allowed is False
    with pytest.raises(FinancialDataMissingError, match="Limite comercial"):
        validate_discount("200", "5", "164.18", None)


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (gross_profit_unit, ("100", None)),
        (gross_margin_percent, ("100", None)),
        (contribution_profit_unit, ("100", None, "0", "0", "0")),
        (minimum_sale_price, (None, "0", "0", "0", "20")),
        (minimum_sale_price, ("100", None, "0", "0", "20")),
    ],
)
def test_dados_financeiros_necessarios_ausentes_nao_viram_zero(function, args):
    with pytest.raises(FinancialDataMissingError):
        function(*args)


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (gross_margin_percent, ("0", "10")),
        (gross_profit_unit, ("-1", "10")),
        (gross_profit_unit, ("100", "-1")),
        (contribution_profit_unit, ("100", "10", "-1", "0", "0")),
        (gross_profit_unit, ("NaN", "10")),
        (minimum_sale_price, ("100", "0", "70", "20", "20")),
        (minimum_sale_price, ("100", "0", "0", "0", "100")),
        (minimum_sale_price, ("100", "0", "0", "0", "-1")),
        (contribution_margin_percent, ("100", "10", "0", "60", "40")),
        (discounted_price, ("100", "101")),
        (maximum_discount_percent, ("0", "10")),
    ],
)
def test_entradas_invalidas_sao_rejeitadas(function, args):
    with pytest.raises(InvalidFinancialInputError):
        function(*args)


def test_limite_comercial_invalido_e_rejeitado():
    with pytest.raises(InvalidFinancialInputError):
        permitted_discount_percent("200", "150", "-1")
