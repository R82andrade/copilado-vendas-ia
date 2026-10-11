# vendas-api

API REST para gerenciamento de clientes, produtos e histórico de compras em uma operação de vendas.

## Funcionalidades

- Cadastro, consulta, atualização e remoção de clientes
- Cadastro, consulta, atualização e remoção de produtos
- Validação de dados e regras de negócio
- Registro de pedidos com itens e cálculo de total
- Validação de desconto máximo por produto
- Testes automatizados com pytest

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- SQLite por padrão
- pytest

## Instalação

1. Crie e ative um ambiente virtual
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Configure o ambiente local:

```bash
copy .env.example .env
```

## Execução

```bash
python -m uvicorn app.main:app --reload
```

A API ficará disponível em:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

## Testes

```bash
python -m pytest -q
```

## Endpoints principais

### Clientes

- POST /clientes/
- GET /clientes/
- GET /clientes/{id}
- PUT /clientes/{id}
- DELETE /clientes/{id}

### Produtos

- POST /produtos/
- GET /produtos/
- GET /produtos/{id}
- PUT /produtos/{id}
- DELETE /produtos/{id}

### Pedidos

- POST /pedidos/
- GET /pedidos/

## Observação

O projeto usa SQLite como banco padrão local para facilitar desenvolvimento e testes. Para produção, basta definir uma URL válida em DATABASE_URL no arquivo .env.
