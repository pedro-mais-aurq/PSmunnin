# Relatório de problemas encontrados — LeadHunter AI

Documento para envio a outra LLM responsável por revisar, corrigir e reimplantar as alterações necessárias.

## Escopo deste documento

Este relatório consolida os problemas encontrados na auditoria do pacote `leadhunter-ai.zip`.

A outra LLM deve aplicar correções no código, na estrutura operacional e na configuração do projeto, respeitando as decisões arquiteturais já adotadas pela equipe.

Não incluir, modificar ou propor novamente a arquitetura das páginas do front-end. Essa parte foi corrigida manualmente pela equipe. Caso seja necessário tocar no front-end, limitar-se a problemas de configuração/build/dependências, sem redesenhar rotas ou layout.

## Resultado da auditoria executada

Foram executadas as seguintes verificações locais:

```bash
python -m compileall -q .
pytest tests/unit/test_score_engine.py -q
```

Resultado observado:

```txt
6 passed
```

A ausência de erro nesses testes não significa que a aplicação esteja funcional em runtime. Foram encontrados erros estáticos e riscos operacionais que podem quebrar rotas da API, workers Celery, persistência no banco e consistência funcional do produto.

---

# Correções obrigatórias

## P0-01 — `MASTER_CONTEXT.md` ausente no pacote

**Severidade:** crítica  
**Área:** documentação/arquitetura  
**Arquivo afetado:** `README.md` e estrutura `docs/`

### Evidência

O `README.md` instrui consultar `MASTER_CONTEXT.md`, mas o arquivo não está presente no pacote analisado.

Trecho relevante:

```md
Ver `MASTER_CONTEXT.md` para especificação completa.
```

### Impacto

Sem o documento de contexto mestre, outra LLM ou outro programador perde a referência arquitetural principal do projeto. Isso aumenta risco de correções contraditórias.

### Correção requerida

Criar ou restaurar:

```txt
docs/MASTER_CONTEXT.md
```

Atualizar o README para apontar explicitamente para:

```md
Ver `docs/MASTER_CONTEXT.md`.
```

### Critério de aceite

- `docs/MASTER_CONTEXT.md` existe no repositório.
- `README.md` aponta para o caminho correto.
- O documento mestre não contradiz a estrutura operacional atual do projeto.

---

## P0-02 — Estrutura do pacote contradiz o monorepo adotado

**Severidade:** crítica  
**Área:** estrutura de repositório  
**Arquivos/pastas afetados:** raiz do projeto

### Evidência

O pacote analisado está organizado assim:

```txt
/app
/frontend
/tests
```

A estrutura previamente adotada pela equipe era monorepo:

```txt
/apps/api
/apps/web
/docs
/packages
/infra
```

Além disso, o README lista `/app`, `/frontend` e `/n8n`, mas a estrutura adotada em conversas anteriores era `apps/api` e `apps/web`.

### Impacto

Essa divergência causa confusão operacional, dificulta colaboração entre Samuel/API e Pedro/front-end, e pode quebrar scripts, Dockerfiles e convenções do projeto.

### Correção requerida

Reorganizar o projeto preservando código existente:

```txt
/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   ├── pytest.ini
│   │   └── Dockerfile
│   └── web/
│       ├── app/
│       ├── public/
│       ├── package.json
│       └── Dockerfile
├── docs/
│   └── MASTER_CONTEXT.md
├── infra/
│   ├── docker-compose.yml
│   └── nginx.conf
├── packages/
└── README.md
```

Ajustar caminhos de Docker, testes e documentação após mover arquivos.

### Critério de aceite

- API fica em `apps/api`.
- Front-end fica em `apps/web`.
- Infra fica em `infra`.
- Documentação fica em `docs`.
- `docker compose` e comandos de teste funcionam após reorganização.

---

## P0-03 — Rota `/leads/{lead_id}` quebra por `Analysis` não importado

**Severidade:** crítica  
**Área:** API/FastAPI  
**Arquivo:** `app/api/routes.py`

### Evidência

A rota usa `Analysis` em:

```python
select(Lead, Company, Score, Analysis)
...
.outerjoin(Analysis)
```

Mas o import atual contém apenas:

```python
from app.domain.models import (
    PipelineRun, PipelineRunStatus, Lead, LeadStatus, Company, Score, OutreachMessage, OutreachStatus, Operator
)
```

### Impacto

Ao chamar `GET /v1/leads/{lead_id}`, a API falha com:

```txt
NameError: name 'Analysis' is not defined
```

### Correção requerida

Adicionar `Analysis` ao import:

```python
from app.domain.models import (
    PipelineRun,
    PipelineRunStatus,
    Lead,
    LeadStatus,
    Company,
    Score,
    OutreachMessage,
    OutreachStatus,
    Operator,
    Analysis,
)
```

### Critério de aceite

- `GET /v1/leads/{lead_id}` não gera `NameError`.
- Teste de integração cobrindo lead com e sem análise passa.

---

## P0-04 — Worker Celery usa `datetime` e `timezone` sem import

**Severidade:** crítica  
**Área:** worker/Celery  
**Arquivo:** `app/workers/tasks.py`

### Evidência

O arquivo usa:

```python
run.started_at = datetime.now(timezone.utc)
...
run.finished_at = datetime.now(timezone.utc)
```

Mas não importa `datetime` nem `timezone`.

### Impacto

A task `run_pipeline_task` quebra em runtime ao tentar iniciar ou finalizar um pipeline.

### Correção requerida

Adicionar no topo de `app/workers/tasks.py`:

```python
from datetime import datetime, timezone
```

### Critério de aceite

- Worker Celery executa a task sem `NameError`.
- Teste ou execução manual de `run_pipeline_task` não falha por imports ausentes.

---

## P0-05 — Dependência `beautifulsoup4` ausente

**Severidade:** crítica  
**Área:** dependências/runtime  
**Arquivos:** `app/agents/analyzer_agent.py`, `requirements.txt`

### Evidência

`analyzer_agent.py` importa:

```python
from bs4 import BeautifulSoup
```

Mas `requirements.txt` não contém `beautifulsoup4`.

### Impacto

Ambiente limpo ou container pode falhar com:

```txt
ModuleNotFoundError: No module named 'bs4'
```

### Correção requerida

Adicionar ao `requirements.txt`:

```txt
beautifulsoup4==4.12.3
```

Ou versão compatível fixada conforme política do projeto.

### Critério de aceite

- Build do container instala `beautifulsoup4`.
- Import de `AnalyzerAgent` funciona em ambiente limpo.

---

## P0-06 — Dois enums `PriorityTier` diferentes causam inconsistência de persistência

**Severidade:** crítica  
**Área:** domínio/persistência  
**Arquivos:** `app/domain/models.py`, `app/domain/score_engine.py`, `app/workers/tasks.py`

### Evidência

Há um enum em `models.py`:

```python
class PriorityTier(PyEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISCARD = "discard"
```

E outro enum separado em `score_engine.py`:

```python
class PriorityTier(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISCARD = "discard"
```

O worker persiste o resultado diretamente:

```python
priority_tier=score.priority_tier
```

### Impacto

`score.priority_tier` vem do enum do `score_engine`, mas o modelo SQLAlchemy espera o enum de `models.py`. Isso pode gerar erro de persistência ou inconsistência silenciosa.

### Correção requerida

Escolher uma das abordagens:

1. Criar um enum único compartilhado no domínio e reutilizá-lo em `models.py` e `score_engine.py`.
2. Converter explicitamente no momento da persistência.

Correção mínima aceitável:

```python
from app.domain.models import PriorityTier as ModelPriorityTier

priority_tier=ModelPriorityTier(score.priority_tier.value)
```

Melhor correção:

```txt
app/domain/enums.py
```

com `PriorityTier` único importado pelos dois módulos.

### Critério de aceite

- Existe apenas uma fonte de verdade para `PriorityTier`, ou há conversão explícita testada.
- Persistência de `Score.priority_tier` funciona em banco real.
- Teste cobre gravação de score com `HOT`, `WARM`, `COLD` e `DISCARD`.

---

## P0-07 — Empresas sem site são descartadas pelo score atual

**Severidade:** crítica  
**Área:** regra de negócio/score  
**Arquivos:** `app/domain/score_engine.py`, `app/domain/services.py`, `tests/unit/test_score_engine.py`

### Evidência

O peso padrão de ausência de site é:

```python
no_website: float = 0.25
```

O threshold mínimo para contato é:

```python
DEFAULT_THRESHOLD = 70
```

O teste atual confirma que empresa sem site recebe apenas 25 pontos e vira `DISCARD`:

```python
assert result.total_score == 25
assert result.priority_tier == PriorityTier.DISCARD
```

### Impacto

O produto busca identificar oportunidades digitais, especialmente empresas sem site ou com presença digital fraca. A regra atual descarta justamente uma das oportunidades centrais.

### Correção requerida

Atualizar a regra de score para que ausência de site seja oportunidade forte, não descarte automático.

Opção simples:

```python
if not analysis.has_website:
    return ScoreResult(
        total_score=85,
        priority_tier=PriorityTier.HOT,
        breakdown={...},
    )
```

Opção por pesos:

```python
no_website: float = 0.60
performance: float = 0.10
seo: float = 0.10
设计/design: float = 0.10
social_presence: float = 0.10
```

Ajustar testes unitários para refletir a regra correta.

### Critério de aceite

- Lead sem site não é `DISCARD` por padrão.
- Lead sem site deve ser ao menos `WARM`, preferencialmente `HOT`, conforme decisão de produto.
- Testes unitários refletem a nova regra.
- Pipeline qualifica corretamente empresas sem site.

---

## P0-08 — Análise de lead sem site não é persistida

**Severidade:** crítica  
**Área:** persistência/dados  
**Arquivo:** `app/workers/tasks.py`

### Evidência

O worker só salva `Analysis` quando:

```python
if analysis.has_website or analysis.load_time_ms is not None:
    db.add(Analysis(...))
```

Se a empresa não tem site, normalmente:

```python
analysis.has_website == False
analysis.load_time_ms is None
```

Logo, nenhuma análise é salva.

### Impacto

A informação “não possui site” se perde no banco, apesar de ser informação central para o produto.

### Correção requerida

Persistir `Analysis` sempre que o lead for analisado:

```python
db.add(Analysis(
    lead_id=lead.id,
    has_website=analysis.has_website,
    load_time_ms=analysis.load_time_ms,
    mobile_friendly=analysis.mobile_friendly,
    has_ssl=analysis.has_ssl,
    seo_title_present=analysis.seo_title_present,
    seo_meta_description_present=analysis.seo_meta_description_present,
    tech_stack_guess=analysis.tech_stack_guess,
    design_age_estimate=analysis.design_age_estimate,
))
```

### Critério de aceite

- Todo lead processado tem registro em `analysis`.
- Lead sem site salva `has_website=False`.
- `GET /v1/leads/{lead_id}` retorna análise mesmo para lead sem site.

---

# Correções importantes

## P1-01 — Filtro de status em `/leads` compara enum com string

**Severidade:** alta  
**Área:** API/FastAPI  
**Arquivo:** `app/api/routes.py`

### Evidência

A rota faz:

```python
if status:
    query = query.where(Lead.status == status)
```

`Lead.status` é enum SQLAlchemy, enquanto `status` chega como string via query parameter.

### Impacto

O filtro pode não funcionar corretamente ou gerar comportamento inconsistente entre banco, driver e SQLAlchemy.

### Correção requerida

Converter a string para `LeadStatus` antes de filtrar:

```python
if status:
    try:
        status_enum = LeadStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status inválido")

    query = query.where(Lead.status == status_enum)
```

### Critério de aceite

- `/v1/leads?status=qualificado` retorna apenas leads qualificados.
- Status inválido retorna HTTP 400, não lista vazia silenciosa nem erro 500.

---

## P1-02 — Transição inválida de status pode retornar HTTP 500

**Severidade:** alta  
**Área:** API/FastAPI  
**Arquivo:** `app/api/routes.py`

### Evidência

A rota converte o novo status, mas não trata erro de transição inválida:

```python
lead.status = LeadStatusTransitionService.transition(lead.status, new_status)
```

O serviço pode lançar:

```python
raise ValueError(f"Transição inválida: {current.value} -> {target.value}")
```

### Impacto

Uma transição inválida vira erro interno 500, quando deveria ser erro de entrada do cliente.

### Correção requerida

```python
try:
    lead.status = LeadStatusTransitionService.transition(lead.status, new_status)
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc))
```

### Critério de aceite

- Transição inválida retorna HTTP 400.
- Transição válida retorna status atualizado.
- Teste de API cobre ambos os casos.

---

## P1-03 — Pesos de score podem ser salvos com soma inválida

**Severidade:** alta  
**Área:** API/configuração de score  
**Arquivos:** `app/api/schemas.py`, `app/api/routes.py`, `app/domain/score_engine.py`

### Evidência

`ScoreWeightsUpdate` valida cada campo entre 0 e 1:

```python
no_website: float = Field(0.25, ge=0, le=1)
performance: float = Field(0.20, ge=0, le=1)
seo: float = Field(0.20, ge=0, le=1)
design: float = Field(0.20, ge=0, le=1)
social_presence: float = Field(0.15, ge=0, le=1)
```

Mas não valida se a soma final é 1.0.

### Impacto

O operador pode salvar pesos inválidos, como soma 2.4 ou 0.3. Isso contradiz a validação existente em `ScoreWeights.__post_init__` e pode gerar score distorcido.

### Correção requerida

Adicionar validação no schema Pydantic ou reutilizar `ScoreWeights` antes de persistir.

Exemplo com Pydantic v2:

```python
from pydantic import model_validator

@model_validator(mode="after")
def validate_total(self):
    total = self.no_website + self.performance + self.seo + self.design + self.social_presence
    if not (0.99 <= total <= 1.01):
        raise ValueError(f"Pesos devem somar 1.0, soma atual: {total}")
    return self
```

### Critério de aceite

- Pesos válidos são salvos.
- Pesos com soma inválida retornam HTTP 422 ou HTTP 400.
- Teste cobre soma válida e inválida.

---

## P1-04 — Alembic configurado, mas migrations não existem

**Severidade:** alta  
**Área:** banco/migrations  
**Arquivos:** `alembic.ini`, estrutura do projeto

### Evidência

`alembic.ini` contém:

```ini
script_location = alembic
```

Mas a pasta `alembic/` não existe no pacote analisado.

### Impacto

O projeto aparenta suportar migrations, mas `alembic upgrade head` não funciona. Isso inviabiliza evolução controlada do schema.

### Correção requerida

Escolher uma estratégia:

1. Para MVP local: remover Alembic temporariamente e usar apenas `Base.metadata.create_all`.
2. Para fluxo profissional: criar migrations reais.

Correção recomendada:

```bash
alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Ajustar `env.py` para importar `Base.metadata`.

### Critério de aceite

- `alembic upgrade head` executa com sucesso, ou Alembic é removido do projeto até ser implementado.
- Estratégia de schema está documentada no README.

---

## P1-05 — `.gitignore` ausente e artefatos gerados incluídos no pacote

**Severidade:** alta  
**Área:** repositório/higiene  
**Arquivos/pastas:** `.gitignore`, `__pycache__/`, `.pytest_cache/`

### Evidência

O pacote analisado não contém `.gitignore` na raiz e inclui arquivos gerados como:

```txt
.pytest_cache/
__pycache__/
*.pyc
```

### Impacto

O repositório pode versionar cache, builds, ambientes locais e dependências, aumentando ruído em commits e risco de vazamento de arquivos locais.

### Correção requerida

Criar `.gitignore` na raiz. Exemplo mínimo:

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
.env

# Node / Next
node_modules/
.next/
out/
dist/
npm-debug.log*

# OS / IDE
.DS_Store
.vscode/
.idea/
```

Observação: se o projeto usa npm, normalmente `package-lock.json` deve ser versionado. Não ignorar lockfile sem decisão explícita da equipe.

### Critério de aceite

- `.gitignore` existe na raiz.
- Caches e arquivos `.pyc` são removidos do versionamento.
- `git status` não mostra artefatos gerados.

---

## P1-06 — README menciona workflows n8n, mas eles não existem

**Severidade:** alta  
**Área:** documentação/automação  
**Arquivos/pastas:** `README.md`, `docker-compose.yml`, `n8n/`

### Evidência

O README lista:

```txt
/n8n # Workflows de automação
```

O `docker-compose.yml` sobe um container `n8n`, mas o pacote não contém pasta `n8n/` nem workflows versionados.

### Impacto

A documentação promete workflows versionados que não existem. Outra LLM pode assumir integrações inexistentes.

### Correção requerida

Escolher uma das opções:

1. Criar:

```txt
n8n/
└── workflows/
```

com workflows exportados versionados.

2. Remover temporariamente a menção a workflows no README até que existam.

### Critério de aceite

- README não promete pasta inexistente.
- Se n8n fizer parte do MVP, workflows exportados estão versionados.

---

# Correções recomendadas

## P2-01 — Front-end pode estar sem configuração TypeScript explícita

**Severidade:** média  
**Área:** front-end/configuração  
**Arquivo:** `frontend/package.json` ou `apps/web/package.json`

### Evidência

O `package.json` analisado continha apenas dependências principais:

```json
{
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  }
}
```

O projeto usa arquivos `.tsx`, mas não havia evidência de:

```txt
typescript
@types/react
@types/node
tsconfig.json
next.config.*
eslint
```

### Impacto

O build do Next.js pode instalar dependências automaticamente ou falhar dependendo do ambiente. Para repositório profissional, a configuração deve ser explícita.

### Correção requerida

Validar se a correção manual do front-end já resolveu este ponto. Se não resolveu, adicionar configuração padrão do Next.js com TypeScript.

Não alterar arquitetura das páginas, rotas ou layout corrigidos manualmente.

### Critério de aceite

- `npm run build` funciona em ambiente limpo.
- TypeScript e tipos necessários estão no `package.json`.
- `tsconfig.json` existe.

---

## P2-02 — Health check retorna valores estáticos `unknown`

**Severidade:** média  
**Área:** observabilidade/API  
**Arquivo:** `app/api/routes.py`

### Evidência

A rota `/health` retorna:

```python
database="unknown"
redis="unknown"
llm_provider="unknown"
```

### Impacto

O endpoint não valida dependências reais. Em Docker/produção, ele pode indicar `status="ok"` mesmo com banco, Redis ou provider indisponíveis.

### Correção requerida

Implementar checagens reais ou renomear para health superficial.

Correção recomendada:

- Fazer ping no banco com `SELECT 1`.
- Fazer ping no Redis.
- Para LLM, validar presença de chave/configuração, sem chamar API paga no health padrão.

### Critério de aceite

- `/v1/health` diferencia dependências disponíveis e indisponíveis.
- Falha de banco ou Redis é refletida no payload e/ou status HTTP conforme política definida.

---

## P2-03 — Celery Beat possui job automático de exemplo que pode consumir APIs reais

**Severidade:** média  
**Área:** worker/operação/custos  
**Arquivo:** `app/workers/tasks.py`

### Evidência

O beat schedule contém:

```python
"daily-pipeline-example": {
    "task": "app.workers.tasks.run_pipeline_task",
    "schedule": crontab(hour=9, minute=0),
    "args": ("auto", "clínicas odontológicas", "Belo Horizonte, MG", 100),
}
```

### Impacto

Ao subir o `beat`, o projeto pode executar coleta real automaticamente, consumindo Google Places API e recursos sem ação explícita do operador.

### Correção requerida

Remover o job de exemplo do schedule padrão ou condicionar por variável de ambiente explícita.

Exemplo:

```python
ENABLE_DAILY_PIPELINE = os.getenv("ENABLE_DAILY_PIPELINE", "false").lower() == "true"
```

### Critério de aceite

- Nenhum pipeline real roda automaticamente sem configuração explícita.
- README documenta como habilitar agendamento real.

---

## P2-04 — Pipeline não marca `PipelineRun` como `FAILED` em falha definitiva

**Severidade:** média  
**Área:** worker/estado do pipeline  
**Arquivo:** `app/workers/tasks.py`

### Evidência

O worker faz retry genérico:

```python
except Exception as exc:
    self.retry(exc=exc, countdown=60)
```

Não há atualização clara do `PipelineRun.status` para `FAILED` após esgotar retries.

### Impacto

Pipeline pode ficar preso como `RUNNING` ou `QUEUED`, dificultando diagnóstico no painel e métricas.

### Correção requerida

Tratar `MaxRetriesExceededError` ou usar `self.request.retries` para marcar falha definitiva.

### Critério de aceite

- Falha temporária faz retry.
- Falha definitiva marca `PipelineRunStatus.FAILED`.
- Erro é registrado/logado.

---

## P2-05 — `OutreachAgent` não trata JSON inválido retornado pelo LLM

**Severidade:** média  
**Área:** agente LLM/robustez  
**Arquivo:** `app/agents/outreach_agent.py`

### Evidência

O agente faz:

```python
data = json.loads(raw)
return OutreachMessage(
    subject=data["subject"],
    body=data["body"],
    personalization_points=analysis_issues[:2],
)
```

Sem tratamento para JSON inválido ou chaves ausentes.

### Impacto

Uma resposta malformada do LLM quebra o pipeline de outreach.

### Correção requerida

Adicionar validação e erro controlado. Preferencialmente usar schema Pydantic para o retorno esperado.

### Critério de aceite

- JSON inválido gera erro controlado e logável.
- Chaves ausentes não causam `KeyError` sem contexto.
- Testes cobrem retorno válido e inválido.

---

## P2-06 — Docker Compose não declara healthchecks/readiness entre serviços

**Severidade:** média  
**Área:** infra/Docker  
**Arquivo:** `docker-compose.yml`

### Evidência

`api`, `worker` e `beat` dependem de `postgres` e `redis` apenas por `depends_on`, sem healthcheck.

### Impacto

Containers podem iniciar antes de banco ou Redis aceitarem conexões, gerando falhas intermitentes no startup.

### Correção requerida

Adicionar healthchecks para `postgres` e `redis` e usar `condition: service_healthy` quando suportado.

### Critério de aceite

- `docker compose up --build` sobe de forma estável.
- API não falha por tentativa prematura de conexão ao Postgres.

---

## P2-07 — Credenciais fracas de exemplo para n8n

**Severidade:** média/baixa  
**Área:** segurança/configuração  
**Arquivo:** `.env.example`

### Evidência

O exemplo define:

```env
N8N_PASSWORD=admin
```

### Impacto

Em ambiente real, há risco de reutilização de senha fraca por cópia direta do `.env.example`.

### Correção requerida

Trocar por placeholder explícito:

```env
N8N_PASSWORD=change-me-use-a-strong-password
```

Documentar que valores de produção devem ser secretos e não versionados.

### Critério de aceite

- `.env.example` não sugere senha trivial.
- `.env` real permanece fora do Git.

---

# Ajustes em testes

## T-01 — Atualizar testes de score para nova regra de empresas sem site

O teste atual espera que lead sem site receba `25` e `DISCARD`. Isso deve mudar após correção da regra de negócio.

Critério esperado:

```python
analysis = AnalysisInput(has_website=False)
result = engine.calculate(analysis)
assert result.total_score >= 70
assert result.priority_tier in {PriorityTier.WARM, PriorityTier.HOT}
```

A equipe deve decidir se sem site será `WARM` ou `HOT`. O teste deve refletir a decisão final.

---

## T-02 — Criar testes de integração para rotas críticas

Criar ou corrigir testes para:

```txt
GET /v1/leads
GET /v1/leads?status=qualificado
GET /v1/leads?status=invalido
GET /v1/leads/{lead_id}
PATCH /v1/leads/{lead_id}/status
PUT /v1/operators/{operator_id}/score-weights
GET /v1/health
```

Casos obrigatórios:

- Lead com análise.
- Lead sem site e com `Analysis.has_website=False` persistido.
- Status inválido retornando 400.
- Transição de status inválida retornando 400.
- Pesos de score inválidos retornando erro.

---

## T-03 — Criar teste de persistência do worker

Cobrir no mínimo:

- Worker cria `Company`.
- Worker cria `Lead`.
- Worker cria `Analysis` mesmo sem site.
- Worker cria `Score` com `PriorityTier` compatível com o modelo SQLAlchemy.
- Pipeline finaliza como `COMPLETED` quando não há erro.
- Pipeline finaliza como `FAILED` quando retries esgotam.

---

# Comandos finais de validação

Após aplicar as correções, executar:

```bash
python -m compileall -q .
pytest -q
```

Se o projeto estiver reorganizado em monorepo, executar a partir dos diretórios corretos:

```bash
cd apps/api
python -m compileall -q .
pytest -q
```

Para front-end, sem alterar a arquitetura das páginas corrigida manualmente:

```bash
cd apps/web
npm install
npm run build
```

Para stack completa:

```bash
docker compose up --build
```

Ou, se o compose foi movido para `infra/`:

```bash
docker compose -f infra/docker-compose.yml up --build
```

# Resultado esperado da implantação corrigida

A outra LLM deve entregar:

1. Código corrigido.
2. Estrutura coerente com monorepo adotado.
3. `MASTER_CONTEXT.md` restaurado em `docs/`.
4. API sem erros de import em runtime.
5. Worker Celery executável.
6. Dependências completas.
7. Score corrigido para empresas sem site.
8. Persistência de `Analysis` para leads sem site.
9. Validação correta de status e pesos.
10. Testes atualizados e passando.
11. Docker Compose funcional.
12. Resumo das alterações aplicadas.

# Instrução final para a LLM que receber este documento

Corrigir os problemas acima sem modificar a arquitetura visual ou estrutural das páginas do front-end, pois essa parte já foi ajustada manualmente. Ao final, fornecer um resumo técnico das mudanças, arquivos alterados e comandos executados com resultados.
