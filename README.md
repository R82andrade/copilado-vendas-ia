# Copiloto de Vendas com IA

API de vendas e atendimento construída com FastAPI, SQLAlchemy e PostgreSQL/SQLite. O frontend administrativo usa React, Vite e React Router e consome os endpoints existentes da API.

## O que já funciona

- Cadastro, edição, consulta e exclusão de clientes.
- Catálogo com cadastro de produtos, preços, estoque e limite de desconto.
- Consulta de pedidos e totais registrados.
- Fila de conversas, histórico de mensagens, atualização de status e envio de respostas.
- Dashboard calculado a partir dos registros reais disponíveis na API.
- Cadastro de usuários e permissões por perfil.
- Deploy de API e painel pelo mesmo App Service, com PostgreSQL Flexible Server.
- Análises de conversas com IA: identifica intenção de compra e objeções, recomenda produtos com base no catálogo e nos pedidos e prepara uma resposta para revisão.
- Histórico persistido de análises, sugestões e decisões: aceitações e rejeições ficam associadas ao usuário; sugestões de resposta passam a enviadas junto com a mensagem real, preservando o texto revisado.

A análise usa a API da OpenAI. Configure `OPENAI_API_KEY` no arquivo `.env`; o texto das mensagens é enviado à OpenAI somente quando um atendente solicita a análise. A resposta sugerida não é enviada automaticamente.

## Atendimento via WhatsApp

O canal usa a WhatsApp Cloud API da Meta. Copie as credenciais da aplicação/conta WhatsApp para o `.env` (`META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_APP_SECRET` e `META_VERIFY_TOKEN`) e reinicie a API. O token de verificação é definido por você e deve ser o mesmo valor configurado no painel da Meta. `META_GRAPH_API_VERSION` é opcional e, se omitido, usa `v23.0`. Não coloque credenciais reais no repositório.

Cadastre `https://<dominio-publico-da-api>/webhooks/whatsapp` como URL de callback no painel Meta, informe o token de verificação e assine o campo `messages` do webhook do WhatsApp Business Account. O endpoint precisa estar publicamente acessível por HTTPS. Mensagens recebidas em texto são deduplicadas pelo ID do provedor; quando o telefone ainda não existe, o sistema cria o cliente e inicia/reutiliza uma conversa WhatsApp. Mensagens recebidas de outros tipos são ignoradas nesta versão.

As respostas dos atendentes em conversas do canal WhatsApp são enviadas pela Cloud API. A Meta aplica a janela de atendimento e pode exigir modelos aprovados fora dela; envio por modelo e callbacks de entrega/leitura ainda não estão implementados, e recusas da Meta são exibidas ao atendente. O webhook não cria lembretes externos: conversas com mensagem do cliente sem resposta por 15 minutos ficam sinalizadas na fila e podem ser filtradas por SLA vencido.

## Estrutura do frontend

```text
frontend/
  src/
    components/   componentes visuais reutilizáveis
    hooks/        carregamento e estado de dados
    layouts/      navegação e estrutura responsiva
    pages/        dashboard, clientes, conversas e demais páginas
    services/     chamadas HTTP e autenticação
    App.jsx       rotas do React Router
    main.jsx      inicialização da aplicação
    styles.css    identidade visual e responsividade
```

## Desenvolvimento local

Instale as dependências Python e prepare o arquivo de ambiente:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edite .env e configure OPENAI_API_KEY com sua chave da API da OpenAI.
```

Inicie a API em um terminal:

```powershell
python -m uvicorn app.main:app --reload
```

Em outro terminal, inicie o frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Com ao menos uma mensagem registrada, abra **Conversas**, selecione o atendimento e use **Analisar conversa** no painel Copiloto IA. O resultado inclui intenção, objeções, recomendações com base no catálogo e nos pedidos, evidências e uma resposta editável. Cada análise e sugestão é salva; aceite uma recomendação ou use a resposta como rascunho. A decisão “enviada” só é registrada quando a mensagem é enviada, junto com o texto final revisado. Consulte o histórico em **Análises da IA** e as decisões em **Sugestões**. Reinicie o backend após alterar `.env`.

Abra `http://localhost:5173`. O Vite encaminha as chamadas `/auth`, `/clientes`, `/conversas`, `/produtos`, `/pedidos` e `/ia` para a API em `http://localhost:8000`. A documentação OpenAPI fica em `http://localhost:8000/docs`.

Para gerar os arquivos de produção do painel:

```powershell
cd frontend
npm run build
```

O FastAPI serve `frontend/dist` quando o build existe. O App Service usa os hooks do `azure.yaml` para gerar esse diretório durante o empacotamento.

## Autenticação e perfis

Com `AUTH_REQUIRED=false`, a API mantém o modo local de desenvolvimento. Em produção, use `AUTH_REQUIRED=true`, defina `AUTH_SECRET` com um segredo aleatório forte e configure `ADMIN_USERNAME` e `ADMIN_PASSWORD`.

O primeiro login cria o usuário administrador no banco. As senhas são armazenadas com PBKDF2; os tokens expiram em oito horas.

| Perfil | Permissões |
| --- | --- |
| `admin` | Todas as rotas e gestão de usuários |
| `atendimento` | Consulta clientes e gerencia conversas e mensagens |
| `vendas` | Gerencia clientes, produtos e pedidos; consulta conversas |
| `leitor` | Consulta dados sem alterá-los |

Administradores podem cadastrar contas na tela **Configurações**. Os endpoints de gestão são `GET /auth/users`, `POST /auth/users` e `PATCH /auth/users/{id}`. A senha inicial deve ter pelo menos 12 caracteres.

## Endpoints disponíveis

- Autenticação: `POST /auth/login`
- Clientes: `GET/POST /clientes/`, `GET/PUT/DELETE /clientes/{id}`
- Produtos: `GET/POST /produtos/`, `GET/PUT/DELETE /produtos/{id}`
- Pedidos: `GET/POST /pedidos/`
- Conversas: `GET/POST /conversas/`, `PATCH /conversas/{id}/status`
- Fila paginada: `GET /conversas/pagina` (busca, status, canal, atendente, intervalo de datas e SLA)
- Atribuição e atendentes: `GET /auth/agents`, `PATCH /conversas/{id}/responsavel`
- Mensagens: `GET /conversas/{id}/mensagens/`, `POST /conversas/{id}/mensagens/`
- Histórico paginado: `GET /conversas/{id}/mensagens/pagina`
- WhatsApp Cloud API: `GET/POST /webhooks/whatsapp` (verificação e eventos), `GET /webhooks/whatsapp/status`
- IA: `GET /ia/status`, `POST /ia/conversas/{id}/analise`, `GET /ia/analises`, `GET /ia/sugestoes`, `POST /ia/sugestoes/{id}/decisao`

## Testes da API

```powershell
python -m pytest -q
```

## Deploy no Azure

O projeto provisiona um App Service e PostgreSQL Flexible Server por meio de `infra/main.bicep`. Com Azure CLI e Azure Developer CLI instalados e autenticados:

```powershell
az login
azd auth login
azd up
```

O hook de empacotamento instala as dependências do frontend e executa o build do Vite antes do deploy. Detalhes e parâmetros secretos estão em [docs/deploy-azure.md](docs/deploy-azure.md).
# Comparação de preços no Mercado Livre

No catálogo, use o ícone de balança ao lado do produto para ver o preço cadastrado e abrir uma busca por anúncios semelhantes no Mercado Livre. A busca abre em outra aba e não exige token nem configuração adicional. Confira se os anúncios têm as mesmas especificações, condição e custos de entrega antes de comparar.