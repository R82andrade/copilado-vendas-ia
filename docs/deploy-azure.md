# Deploy no Azure

O deploy publica API e painel no mesmo App Service. O painel chama a API na mesma origem. O banco usa PostgreSQL Flexible Server com backup diário de sete dias.

## Pré-requisitos

- Azure CLI autenticado em uma assinatura com permissão para criar App Service e PostgreSQL Flexible Server.
- Azure Developer CLI (`azd`) instalado.
- Docker instalado se quiser construir a imagem localmente; `azd up` usa o build do App Service.

## Publicar

Na raiz do projeto, execute:

```powershell
az login
azd auth login
azd up
```

Escolha a assinatura e a região quando solicitado. O provisionamento pede os parâmetros secretos do banco, da chave de sessão e da senha inicial do administrador. Use senhas alfanuméricas de 16 a 32 caracteres para PostgreSQL e um segredo aleatório de pelo menos 32 caracteres para `authSecret`. Não reutilize a senha do banco como senha do painel.

Ao final, o `azd` mostra a URL do painel/API. A rota `/docs` exibe a documentação da API.

## Perfis disponíveis

| Perfil | Acesso |
| --- | --- |
| `admin` | Gerencia usuários e acessa todas as operações |
| `atendimento` | Consulta clientes e gerencia conversas e mensagens |
| `vendas` | Gerencia clientes, produtos e pedidos; consulta conversas |
| `leitor` | Consulta dados sem alterá-los |

O primeiro administrador é criado a partir de `ADMIN_USERNAME` e `ADMIN_PASSWORD` na primeira autenticação. Usuários adicionais podem ser criados no painel ou via `POST /auth/users`, com senha inicial de pelo menos 12 caracteres. A administração também está disponível em `GET /auth/users` e `PATCH /auth/users/{id}`.

## Desenvolvimento local

Copie `.env.example` para `.env`, instale `requirements.txt` e rode a API:

```powershell
python -m uvicorn app.main:app --reload
```

Abra `http://localhost:8000` para o painel e `http://localhost:8000/docs` para a API. Também é possível servir `frontend/` na porta 3000; nesse caso, a configuração local aponta o painel para `http://localhost:8000`.
