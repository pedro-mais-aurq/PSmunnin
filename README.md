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
OSM_USER_AGENT=PSMunninMVP/1.0
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
OSM_USER_AGENT=PSMunninMVP/1.0
```

Não inclua `/PSmunnin` em `CORS_ORIGINS`.

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
