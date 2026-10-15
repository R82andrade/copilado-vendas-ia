"""Create the legacy application schema when missing, preserving existing tables."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0001_legacy_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Existing tables are preserved; missing legacy tables are created for new DBs.
    tables = set(inspect(op.get_bind()).get_table_names())
    if "clientes" not in tables:
        op.create_table(
            "clientes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(150), nullable=False),
            sa.Column("cpf", sa.String(14), nullable=True, unique=True),
            sa.Column("telefone", sa.String(20), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("data_cadastro", sa.Date(), nullable=False),
        )
    if "usuarios" not in tables:
        op.create_table(
            "usuarios",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(80), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(300), nullable=False),
            sa.Column("role", sa.String(30), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False),
        )
    if "produtos" not in tables:
        op.create_table(
            "produtos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(150), nullable=False),
            sa.Column("marca", sa.String(100), nullable=False),
            sa.Column("categoria", sa.String(100), nullable=False),
            sa.Column("preco", sa.Float(), nullable=False),
            sa.Column("estoque", sa.Integer(), nullable=False),
            sa.Column("desconto_maximo", sa.Float(), nullable=False),
        )
    if "conversas" not in tables:
        op.create_table(
            "conversas",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
            sa.Column("assunto", sa.String(200), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("resultado", sa.String(40), nullable=False, server_default="sem_resultado"),
            sa.Column("canal", sa.String(50), nullable=False),
            sa.Column("data_criacao", sa.DateTime(), nullable=False),
            sa.Column("ultima_atualizacao", sa.DateTime(), nullable=False),
        )
    if "mensagens" not in tables:
        op.create_table(
            "mensagens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas.id"), nullable=False),
            sa.Column("remetente", sa.String(50), nullable=False),
            sa.Column("texto", sa.Text(), nullable=False),
            sa.Column("data_envio", sa.DateTime(), nullable=False),
        )
    if "pedidos" not in tables:
        op.create_table(
            "pedidos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
            sa.Column("data_pedido", sa.Date(), nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
        )
    if "itens_pedido" not in tables:
        op.create_table(
            "itens_pedido",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pedido_id", sa.Integer(), sa.ForeignKey("pedidos.id"), nullable=False),
            sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
            sa.Column("quantidade", sa.Integer(), nullable=False),
            sa.Column("preco_unitario", sa.Float(), nullable=False),
            sa.Column("desconto_aplicado", sa.Float(), nullable=False),
            sa.Column("subtotal", sa.Float(), nullable=False),
        )
    if "conversas_responsaveis" not in tables:
        op.create_table(
            "conversas_responsaveis",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas.id", ondelete="CASCADE"),
                      nullable=False, unique=True),
            sa.Column("username", sa.String(80), nullable=False),
            sa.Column("atribuido_por", sa.String(80), nullable=False),
            sa.Column("atribuido_em", sa.DateTime(), nullable=False),
        )
    if "mensagens_canais" not in tables:
        op.create_table(
            "mensagens_canais",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("mensagem_id", sa.Integer(), sa.ForeignKey("mensagens.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("provider_message_id", sa.String(200), nullable=False),
            sa.Column("direction", sa.String(10), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("error_detail", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("provider", "provider_message_id", name="uq_provider_message"),
        )
    if "analises_ia" not in tables:
        op.create_table(
            "analises_ia",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas.id"), nullable=False),
            sa.Column("criado_por", sa.String(80), nullable=False),
            sa.Column("modelo", sa.String(100), nullable=False),
            sa.Column("intencao", sa.Text(), nullable=False),
            sa.Column("justificativa_intencao", sa.Text(), nullable=False),
            sa.Column("objecoes", sa.JSON(), nullable=False),
            sa.Column("produtos_recomendados", sa.JSON(), nullable=False),
            sa.Column("evidencias", sa.JSON(), nullable=False),
            sa.Column("resposta_sugerida", sa.Text(), nullable=False),
            sa.Column("confianca", sa.String(20), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
        )
    if "sugestoes_ia" not in tables:
        op.create_table(
            "sugestoes_ia",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("analise_id", sa.Integer(), sa.ForeignKey("analises_ia.id"), nullable=False),
            sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas.id"), nullable=False),
            sa.Column("tipo", sa.String(20), nullable=False),
            sa.Column("conteudo", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
        )
    if "decisoes_ia" not in tables:
        op.create_table(
            "decisoes_ia",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("sugestao_id", sa.Integer(), sa.ForeignKey("sugestoes_ia.id"), nullable=False),
            sa.Column("decisao", sa.String(20), nullable=False),
            sa.Column("decidido_por", sa.String(80), nullable=False),
            sa.Column("decidido_em", sa.DateTime(), nullable=False),
            sa.Column("mensagem_id", sa.Integer(), sa.ForeignKey("mensagens.id"), nullable=True),
            sa.Column("texto_enviado", sa.Text(), nullable=True),
        )


def downgrade():
    # Never remove legacy tables or application data.
    pass
