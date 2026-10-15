# Copiloto de Vendas com IA

API de vendas e atendimento construída com FastAPI, SQLAlchemy e PostgreSQL/SQLite. O frontend administrativo usa React, Vite e React Router e consome os endpoints existentes da API.

## O que já funciona

- Cadastro, edição, consulta e exclusão de clientes.
- Catálogo com cadastro de produtos, preços, estoque e limite de desconto. O painel calcula e exibe o preço final aplicando o desconto máximo permitido.
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
python -m alembic upgrade head
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

## Pesquisa de preços em outras lojas

No **Catálogo de produtos**, o preço com desconto máximo é calculado assim:

```text
preço final = preço cadastrado × (1 − desconto máximo / 100)
```

Use o ícone de balança em um produto para abrir a comparação. A janela mostra o preço cadastrado, permite atualizá-lo e apresenta o preço com o desconto máximo. O termo de busca começa com a marca e o nome do produto, mas pode ser editado.

Os botões abrem buscas públicas em outra aba no Google Shopping, Amazon Brasil, Magalu, Shopee e Mercado Livre. Essa busca não exige token, senha nem configuração adicional no projeto. Os resultados e preços são exibidos pelos próprios sites; o sistema não coleta nem atualiza ofertas automaticamente. Para comparar, confira modelo, especificações, condição e frete. Uma loja pode solicitar login para concluir uma compra.

## Módulo financeiro

O catálogo calcula rentabilidade estimada e valida descontos antes de registrar um pedido. Custos unitários ficam opcionais em `produtos`: `custo_aquisicao`, `outros_custos_variaveis`, `margem_contribuicao_minima` e `limite_desconto_comercial`. Valores monetários usam `NUMERIC(12,2)`/`Decimal`; percentuais usam `NUMERIC(5,2)`. Valores vazios significam desconhecidos, não zero.

A política global fica em `configuracoes_financeiras`, com imposto variável, comissão, margem mínima e limite comercial. Uma definição individual de margem ou desconto no produto prevalece sobre a global. Informe custo zero somente quando o responsável confirmar que não há esse custo.

O campo de desconto máximo já existente no catálogo continua sendo um teto adicional. O limite usado é o menor entre esse teto legado e o limite financeiro/comercial configurado, para que a nova funcionalidade não aumente permissões de desconto existentes.

Fórmulas usadas (percentuais em escala 0 a 100):

```text
lucro bruto = preço final - custo de aquisição
margem bruta (%) = lucro bruto / preço final * 100
contribuição = preço final - aquisição - outros custos - preço final * (imposto + comissão) / 100
margem de contribuição (%) = contribuição / preço final * 100
preço mínimo = (aquisição + outros custos) / (1 - (imposto + comissão + margem mínima) / 100)
desconto financeiro máximo (%) = max(0, (preço atual - preço mínimo) / preço atual * 100)
desconto permitido = menor entre desconto financeiro máximo e limite comercial
```

Margem é calculada sobre o preço de venda; markup é calculado sobre o custo. Custos fixos e despesas rateadas não entram nessas estimativas, portanto o resultado não é lucro líquido. Os percentuais tributários e comerciais devem ser confirmados pelo responsável da loja ou contador.

### Endpoints financeiros

- `GET /financeiro/produtos/{id}`: consulta parâmetros e cálculos do produto.
- `PUT /financeiro/produtos/{id}`: atualiza custos e limites específicos (somente administrador).
- `GET /financeiro/configuracao`: consulta a política global (somente administrador).
- `PUT /financeiro/configuracao`: cria ou atualiza a política global (somente administrador).
- `POST /financeiro/produtos/{id}/simulacoes`: simula `desconto_percentual` ou `preco_final_pretendido` (administrador ou vendas).
- `POST /ia/produtos/{id}/recomendacao-financeira`: pede explicação revisável dos resultados calculados (administrador ou vendas).

Exemplo de configuração e simulação:

```text
PUT /financeiro/configuracao
Content-Type: application/json
{"imposto_variavel_percentual":8,"comissao_percentual":5,"margem_contribuicao_minima":20,"limite_desconto_comercial":15}

PUT /financeiro/produtos/1
Content-Type: application/json
{"custo_aquisicao":100,"outros_custos_variaveis":10}

POST /financeiro/produtos/1/simulacoes
Content-Type: application/json
{"desconto_percentual":10}
```

Resposta resumida para esse exemplo (supondo limite legado do catálogo de pelo menos 15%):

```json
{
  "situacao": "permitida",
  "preco_original": 200,
  "desconto_percentual": 10,
  "valor_desconto": 20,
  "preco_final": 180,
  "custo_aquisicao": 100,
  "outros_custos_variaveis": 10,
  "imposto_variavel_valor": 14.4,
  "comissao_valor": 9,
  "lucro_bruto": 80,
  "margem_bruta_percentual": 44.44,
  "contribuicao_unitaria": 46.6,
  "margem_contribuicao_percentual": 25.89,
  "preco_minimo": 164.18,
  "limite_financeiro_desconto_percentual": 17.91,
  "limite_comercial_desconto_percentual": 15,
  "limite_permitido_desconto_percentual": 15,
  "motivo": null
}
```

Os cálculos e bloqueios são feitos no backend. `admin` pode consultar e alterar dados financeiros; `vendas` pode consultar e simular; `atendimento` e `leitor` não têm acesso financeiro. Os schemas públicos de produto não incluem custos ou margens. O endpoint de pedidos recusa descontos positivos quando faltam dados financeiros e bloqueia propostas fora da política.

### Migrações e testes

Alembic está configurado com migração aditiva e campos opcionais. Para aplicar em banco existente, faça o backup operacional habitual e execute na raiz do projeto:

```powershell
python -m pip install -r requirements.txt
python -m alembic upgrade head
```

A revisão base cria o schema legado em um banco novo e deixa tabelas existentes intactas. A revisão financeira acrescenta colunas `NULL` e cria a tabela da política. O downgrade não apaga os dados; reversões devem ser planejadas como procedimento manual revisado. PostgreSQL e SQLite usam tipos `NUMERIC`.

```powershell
python -m pytest tests/test_financeiro.py tests/test_financeiro_api.py tests/test_financeiro_migration.py tests/test_compra.py -q
python -m pytest -q
```

A comparação automática de ofertas concorrentes continua planejada porque ainda não há fonte estruturada de preços reais. A IA explica dados calculados, não autoriza descontos e não altera valores automaticamente.

Descontos fora da política são bloqueados. Esta entrega ainda não possui fila interna de solicitação e aprovação excepcional; se a loja autorizar uma exceção, um administrador precisa revisar e ajustar a política antes do registro do pedido. A compatibilidade da migração foi exercitada em SQLite; a migração PostgreSQL usa operações aditivas e tipos `NUMERIC`, mas ainda deve ser validada no ambiente PostgreSQL de implantação.
