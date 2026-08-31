# PS Munnin

MVP de prospecção automatizada para identificar empresas locais com baixa
maturidade digital.

## Arquitetura

```text
GitHub Pages
    ↓
Next.js estático
    ↓
FastAPI no Render
    ↓
MongoDB
    ↓
Nominatim + Overpass + análise de websites
```

## Estrutura

```text
.
├── .github/
│   └── workflows/
│       └── deploy-frontend.yml
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   ├── requirements.local.txt
│   ├── pytest.ini
│   ├── .python-version
│   ├── .env.example
│   └── tests/
├── docs/
│   └── PRD.md
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── package-lock.json
│   ├── next.config.mjs
│   ├── eslint.config.mjs
│   ├── tsconfig.json
│   ├── .env.example
│   └── SECURITY_NOTES.md
├── .gitignore
└── README.md
```

## Requisitos

* Python 3.12.
* Node.js 20 ou superior.
* MongoDB local ou MongoDB Atlas.
* npm.

## Backend local

```bash
cd backend
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux ou macOS:

```bash
source .venv/bin/activate
```

Instalação:

```bash
pip install -r requirements.local.txt
```

Crie `backend/.env` a partir de `backend/.env.example`:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=psmunnin
CORS_ORIGINS=http://localhost:3000
OSM_USER_AGENT=PSMunnin/0.2 (+https://github.com/pedro-mais-aurq/PSmunnin)
OVERPASS_ENDPOINTS=https://overpass.private.coffee/api/interpreter,https://maps.mail.ru/osm/tools/overpass/api/interpreter,https://overpass-api.de/api/interpreter
```

Inicie:

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```text
http://localhost:8000/api/health
```

Swagger:

```text
http://localhost:8000/docs
```

## Frontend local

```bash
cd frontend
npm ci
```

Crie `frontend/.env.local` a partir de `frontend/.env.example`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BASE_PATH=
```

Inicie:

```bash
npm run dev
```

Acesse:

```text
http://localhost:3000
```

## Testes e validações

Backend:

```bash
cd backend
python -m compileall .
pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run type-check
npm run lint
npm run build
```

`npm run check` reúne a verificação de tipos e o lint. Para os testes de
classificação dos erros de polling, sem chamadas de rede:

```bash
cd frontend
node --test src/test/api.test.mjs
```

O comando `npm run type-check` executa primeiro `next typegen` para gerar os
tipos internos do Next.js antes de executar o TypeScript.

## Deploy do backend no Render

Configure um Web Service com:

```text
Root Directory:
backend

Build Command:
pip install -r requirements.txt

Start Command:
uvicorn server:app --host 0.0.0.0 --port $PORT

Health Check Path:
/api/health
```

Variáveis obrigatórias:

```env
MONGO_URL=<conexão real do MongoDB>
DB_NAME=psmunnin
CORS_ORIGINS=https://pedro-mais-aurq.github.io,http://localhost:3000
OSM_USER_AGENT=PSMunnin/0.2 (+https://github.com/pedro-mais-aurq/PSmunnin)
```

Não inclua `/PSmunnin` em `CORS_ORIGINS`.

### Resiliência da coleta Overpass

`OVERPASS_ENDPOINTS` é opcional. Quando ausente, utiliza três infraestruturas
independentes nesta ordem: Private Coffee → VK Maps (`maps.mail.ru`) →
`overpass-api.de`. O último permanece como fallback final. Para sobrescrever o pool:

```env
OVERPASS_ENDPOINTS=https://overpass.private.coffee/api/interpreter,https://maps.mail.ru/osm/tools/overpass/api/interpreter,https://overpass-api.de/api/interpreter
```

Separe as URLs por vírgula. Espaços e entradas vazias são removidos, e URLs
repetidas são deduplicadas. Uma variável definida sem nenhuma URL válida gera
erro claro na inicialização; omita a variável para usar os defaults. As URLs
devem ser HTTP(S), sem credenciais, query string ou fragmento. Não coloque
tokens nessa variável. As variáveis de produção não são alteradas pelo patch.

Se o Render já tiver `OVERPASS_ENDPOINTS` com a lista anterior, ela continuará
sobrescrevendo os defaults após o deploy. Atualize-a manualmente para os três
endpoints acima, ou remova a variável para usar o novo padrão.

A coleta faz **uma rodada completa por três infraestruturas independentes**,
interrompendo no primeiro resultado válido. Há no máximo três chamadas no pool
padrão, sem repetir servidores nem aguardar backoff. Isso reduz a latência em
caso de indisponibilidade e amplia a diversidade de infraestrutura consultada.
Timeouts HTTPX mantidos: conexão 10 s, leitura 45 s, escrita 10 s,
pool 10 s. Esses valores são limites por fase de I/O, não um prazo total da pesquisa.
Falhas de transporte, HTTP 429/5xx e respostas inválidas permitem failover.
JSON deve conter uma lista `elements` de objetos e não pode indicar falha de
execução em `remark`; uma lista vazia válida é aceita.

Outros HTTP 4xx (e redirecionamentos inesperados) encerram a consulta com erro
controlado 502 de rejeição, sem tentar mascarar o problema como indisponibilidade.
O status original e trechos de diagnóstico permitidos são registrados nos logs,
sem copiar corpo arbitrário da resposta. Quando o pool se esgota, a exceção
controlada é 503 e o pipeline persiste `failed` com mensagem amigável. Isso não
muda o contrato assíncrono: `POST /api/searches` continua retornando 202 e
`GET /api/searches/{id}` continua retornando 200 com o estado da pesquisa.

Para investigar no Render, filtre os logs por `search=<UUID>`. Cada tentativa
Overpass registra `provider`, `endpoint`, `attempt`, `round` e `result`, além de
status HTTP e tipo da exceção quando aplicáveis. A numeração de `attempt` é
global na coleta (1 a 3 para o pool padrão), sempre com `round=1`. Se todos
falharem, o log final termina com `attempt=3 round=1 result=unavailable`, o tipo
do último erro e `failures=[...]`, contendo endpoint, tipo do erro e status HTTP
quando existir para cada falha. Não inclui corpo arbitrário, headers ou tokens.
O resumo e os tracebacks ficam apenas nos logs; a mensagem amigável do frontend
não muda. O heartbeat permanece ativo durante a coleta.

O polling continua apenas em `pending`/`running` e para em `done`/`failed`.
Erros da própria consulta HTTP permitem nova tentativa somente para falhas de
rede, timeout, HTTP 408/429/5xx; outros 4xx e falta de configuração não entram em
repetição. `search.error` continua aparecendo na interface.

### Diagnóstico manual de conectividade

No Render Shell, com a raiz do serviço em `backend/`, execute:

```bash
python -m scripts.check_overpass
```

Se estiver na raiz do repositório local:

```bash
cd backend
python -m scripts.check_overpass
```

O script consulta cada endpoint individualmente, mesmo que o primeiro funcione,
uma única vez, usando uma query de no máximo um elemento OSM. Usa a mesma
configuração de endpoints, User-Agent e timeouts da aplicação, centralizada em
`backend/overpass_config.py`. Lê `backend/.env` sem sobrescrever variáveis do
ambiente. Não importa o pipeline nem exige `MONGO_URL`/`DB_NAME`; não lê nem
modifica banco de dados. Imprime endpoint, status, resultado e tempo aproximado,
sem corpo da resposta, headers ou mensagens brutas de exceções.

O código de saída é 0 se todos retornarem JSON válido e 1 se qualquer endpoint
falhar. `python -m scripts.check_overpass --help` mostra as instruções sem fazer
requisições. A execução sem `--help` faz chamadas reais: use somente sob demanda,
nunca como parte do CI ou como um monitor de alta frequência.

### CI de backend

O workflow `.github/workflows/backend-tests.yml` executa em pushes para `correcao`
com mudanças em `backend/**` ou no próprio workflow, e em pull requests que
alterem esses mesmos caminhos. Usa Python 3.12, instala
`backend/requirements.local.txt` e executa `pytest -q` em `backend/`.

Falhas dos testes interrompem o job. A suíte usa HTTP simulado; o diagnóstico
manual nunca é executado no workflow. A integração opcional com MongoDB fica
desativada em CI. O workflow cria uma verificação; para bloquear merges ou um
deploy independente do Render, configure esse check como obrigatório nas regras
do repositório e a política de deploy apropriada. O patch não altera essas regras.


## Deploy do frontend no GitHub Pages

O workflow é acionado por push na branch:

```text
correcao
```

Crie a variável de repositório:

```text
NEXT_PUBLIC_API_URL=https://ps-munnin.onrender.com
```

Caminho:

```text
Settings
→ Secrets and variables
→ Actions
→ Variables
```

Em:

```text
Settings
→ Pages
→ Build and deployment
```

selecione:

```text
Source: GitHub Actions
```

O workflow gera e publica:

```text
frontend/out
```

O `basePath` é calculado automaticamente pelo workflow a partir do nome do
repositório.

O favicon usa a convenção nativa `frontend/src/app/icon.svg`, com a mesma arte
do logo público. O Next.js gera a metadata e exporta `out/icon.svg`; não existe
mais um SVG renomeado para `.ico`. O logo público continua disponível para os
componentes visuais. Para simular o caminho do GitHub Pages no build local,
configure `NEXT_PUBLIC_BASE_PATH=/PSmunnin`.

## Fluxo da aplicação

1. O formulário envia `POST /api/searches`.
2. O backend retorna a pesquisa com status `pending`.
3. O frontend consulta `GET /api/searches/{id}`.
4. O status evolui para `running`.
5. A conclusão retorna `done` e os leads.
6. Erros retornam `failed` com mensagem legível.
7. O operador seleciona um lead.
8. O frontend consulta `/api/leads/{id}/message`.
9. A mensagem é copiada manualmente.

## Segurança do frontend

Os advisories identificados pelo `npm audit` estão documentados em:

```text
frontend/SECURITY_NOTES.md
```

Não utilize `npm audit fix --force`.

## Limitação do MVP

O processamento assíncrono ainda ocorre dentro do processo FastAPI. Cada
pesquisa ativa mantém um heartbeat no MongoDB. Durante um desligamento normal,
somente as pesquisas pertencentes à instância encerrada são marcadas como
`failed`. Após uma falha abrupta, um monitor marca como `failed` apenas pesquisas
sem heartbeat recente. A adoção de uma fila externa pertence a uma etapa futura
e não faz parte deste deploy.
