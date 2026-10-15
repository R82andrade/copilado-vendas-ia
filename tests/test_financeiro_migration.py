import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def test_migration_adds_financial_schema_and_preserves_legacy_product(tmp_path):
    database_path = tmp_path / "legacy.sqlite"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE produtos (id INTEGER PRIMARY KEY, nome VARCHAR(150) NOT NULL, "
            "marca VARCHAR(100) NOT NULL, categoria VARCHAR(100) NOT NULL, preco FLOAT NOT NULL, "
            "estoque INTEGER NOT NULL, desconto_maximo FLOAT NOT NULL)"
        ))
        connection.execute(text(
            "INSERT INTO produtos (id, nome, marca, categoria, preco, estoque, desconto_maximo) "
            "VALUES (7, 'Produto preservado', 'Marca', 'Categoria', 123.45, 3, 10)"
        ))
    engine.dispose()

    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    migrated = create_engine(f"sqlite:///{database_path.as_posix()}")
    columns = {column["name"] for column in inspect(migrated).get_columns("produtos")}
    with migrated.connect() as connection:
        product = connection.execute(text("SELECT * FROM produtos WHERE id=7")).mappings().one()
        config_exists = "configuracoes_financeiras" in inspect(connection).get_table_names()
    assert {"custo_aquisicao", "outros_custos_variaveis", "margem_contribuicao_minima", "limite_desconto_comercial"} <= columns
    assert product["nome"] == "Produto preservado"
    assert product["preco"] == 123.45
    assert product["custo_aquisicao"] is None
    assert config_exists
    migrated.dispose()


def test_migrations_create_schema_for_a_new_database(tmp_path):
    database_path = tmp_path / "new.sqlite"
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    migrated = create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = inspect(migrated)
    assert {"clientes", "usuarios", "produtos", "pedidos", "conversas", "configuracoes_financeiras"} <= set(inspector.get_table_names())
    product_columns = {column["name"] for column in inspector.get_columns("produtos")}
    assert "custo_aquisicao" in product_columns
    migrated.dispose()
