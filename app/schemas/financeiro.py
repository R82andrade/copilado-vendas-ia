from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Money = Decimal
Percent = Decimal


class FinanceProductUpdate(BaseModel):
    custo_aquisicao: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    outros_custos_variaveis: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    margem_contribuicao_minima: Percent | None = Field(default=None, ge=0, lt=100, max_digits=5, decimal_places=2)
    limite_desconto_comercial: Percent | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)


class FinanceProductResponse(FinanceProductUpdate):
    produto_id: int

    model_config = ConfigDict(from_attributes=True)


class FinanceConfigUpdate(BaseModel):
    imposto_variavel_percentual: Percent | None = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    comissao_percentual: Percent | None = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    margem_contribuicao_minima: Percent | None = Field(ge=0, lt=100, max_digits=5, decimal_places=2)
    limite_desconto_comercial: Percent | None = Field(ge=0, le=100, max_digits=5, decimal_places=2)

    @model_validator(mode="after")
    def compatible_percentage_sum(self):
        values = (
            self.imposto_variavel_percentual,
            self.comissao_percentual,
            self.margem_contribuicao_minima,
        )
        if all(value is not None for value in values) and sum(values, Decimal("0")) >= Decimal("100"):
            raise ValueError("Impostos, comissão e margem mínima somados devem ser menores que 100%.")
        return self


class DiscountSimulationRequest(BaseModel):
    desconto_percentual: Percent | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    preco_final_pretendido: Money | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def exactly_one_proposal(self):
        if (self.desconto_percentual is None) == (self.preco_final_pretendido is None):
            raise ValueError("Informe desconto_percentual ou preco_final_pretendido, mas não ambos.")
        return self
