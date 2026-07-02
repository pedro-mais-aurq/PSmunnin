# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

### Planejado

Esta seção é atualizada a cada Sprint com os itens formalmente planejados para a próxima versão, conforme o backlog oficial do projeto. Nenhum item é adicionado aqui sem estar previamente registrado como Issue no repositório.

---

## [1.1.0] - Sprint 2.1

### Adicionado

- Documentação oficial de estrutura do repositório em `docs/PROJECT_STRUCTURE.md`, formalizando a organização do monorepo (`apps`, `packages`, `infra`).
- Documentação oficial de arquitetura em `docs/ARCHITECTURE.md`, detalhando Clean Architecture, DDD, SOLID, Repository Pattern, Service Layer, Dependency Injection, Event-Driven Architecture e Modular Monolith aplicados ao projeto.
- Documentação oficial de convenções de desenvolvimento em `docs/DEVELOPMENT_CONVENTIONS.md`, cobrindo estilo de código Python, nomeação, testes e checklist de Pull Request.
- Documentação oficial de fluxo de Git em `docs/GIT_WORKFLOW.md`, formalizando Git Flow, Conventional Commits, code review e versionamento semântico.
- Registro da primeira Architecture Decision Record do projeto em `docs/ADRs/ADR-001-architecture.md`, justificando a adoção de Clean Architecture, DDD, Repository Pattern, Service Layer, Event-Driven Architecture e Modular Monolith, incluindo a estratégia oficial de evolução (Modular Monolith → Module Extraction → Microservices).
- Catálogo formal de eventos de domínio do fluxo de prospecção (`CompanyCollectedEvent`, `LeadQualifiedEvent`, `LeadScoredEvent`, `LeadApprovedEvent`, `LeadRejectedEvent`, `ProposalGeneratedEvent`, `EmailSentEvent`, `FollowUpDueEvent`).
- Estrutura oficial de referência da API em `docs/API_REFERENCE.md`, existente desde o início do projeto para ser preenchida incrementalmente a cada novo endpoint implementado.
- Capítulo de Dependency Rules em `docs/PROJECT_STRUCTURE.md`, formalizando o fluxo obrigatório de dependência `Controllers/Agents → Services → Repositories → Database`.
- Diagrama de fluxo completo do pipeline de negócio em `docs/ARCHITECTURE.md`, alinhado ao fluxo oficial descrito em `MASTER_CONTEXT.md` (`Scout Agent → Presence Agent → Website Agent → Score Engine → Proposal Agent → Human Approval → Email Agent → CRM`).

### Alterado

- Não aplicável — esta é a primeira formalização documental completa do projeto.

### Corrigido

- Não aplicável nesta Sprint, que possui escopo exclusivamente documental e arquitetural, sem alteração de código de aplicação.

---

## [1.0.0] - Sprint 1.0

### Adicionado

- Estrutura inicial do monorepo LeadHunter AI (`apps/api`, `apps/worker`, `apps/web`).
- Definição inicial do documento `MASTER_CONTEXT.md` como fonte de verdade do projeto.
- Configuração inicial de stack: Next.js e TailwindCSS no frontend; FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis e Celery no backend.

---

## [0.1.0] - Sprint 0.1

### Adicionado

- Repositório inicial do projeto.
- Documentação inicial do produto e do fluxo de negócio em `MASTER_CONTEXT.md`.
- Primeira definição da arquitetura do projeto, base para a formalização completa realizada na Sprint 2.1.

---

## Convenções deste Changelog

### Categorias utilizadas

| Categoria | Significado |
|---|---|
| `Adicionado` | Novas funcionalidades, documentos ou capacidades |
| `Alterado` | Mudanças em funcionalidades já existentes |
| `Descontinuado` | Funcionalidades que serão removidas em versão futura major |
| `Removido` | Funcionalidades removidas nesta versão |
| `Corrigido` | Correções de bugs |
| `Segurança` | Correções relacionadas a vulnerabilidades |

### Regras de atualização

- Toda entrada em `[Não lançado]` deve ser movida para uma versão taggeada apenas no momento do merge de uma branch `release/*` em `main`, conforme `GIT_WORKFLOW.md`.
- Toda entrada referencia o contexto de negócio da mudança, nunca apenas o nome técnico do commit.
- A numeração de versão segue estritamente o Versionamento Semântico descrito em `GIT_WORKFLOW.md`.
