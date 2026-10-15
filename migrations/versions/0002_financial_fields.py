"""Add nullable product costs and global financial settings."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_financial_fields"
down_revision = "0001_legacy_baseline"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "produtos" not in tables:
        raise RuntimeError("Tabela produtos ausente. Inicialize o schema legado antes desta migração.")
    columns = {column["name"] for column in inspector.get_columns("produtos")}
    for name, type_ in (("custo_aquisicao", sa.Numeric(12, 2)),
                        ("outros_custos_variaveis", sa.Numeric(12, 2)),
                        ("margem_contribuicao_minima", sa.Numeric(5, 2)),
                        ("limite_desconto_comercial", sa.Numeric(5, 2))):
        if name not in columns:
            op.add_column("produtos", sa.Column(name, type_, nullable=True))
    if "conversas" in tables:
        conversation_columns = {column["name"] for column in inspector.get_columns("conversas")}
        if "resultado" not in conversation_columns:
            op.add_column("conversas", sa.Column("resultado", sa.String(40), nullable=False,
                                                  server_default="sem_resultado"))
    if "configuracoes_financeiras" not in tables:
        op.create_table(
            "configuracoes_financeiras",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("imposto_variavel_percentual", sa.Numeric(5, 2), nullable=True),
            sa.Column("comissao_percentual", sa.Numeric(5, 2), nullable=True),
            sa.Column("margem_contribuicao_minima", sa.Numeric(5, 2), nullable=True),
            sa.Column("limite_desconto_comercial", sa.Numeric(5, 2), nullable=True),
            sa.Column("responsavel_username", sa.String(80), nullable=True),
        )


def downgrade():
    # Finance data may exist; downgrade deliberately retains it.
    pass
