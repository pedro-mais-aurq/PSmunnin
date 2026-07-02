# API_REFERENCE.md

**Projeto:** LeadHunter AI
**Documento:** Referência Oficial da API HTTP
**Versão:** 1.0.0
**Sprint de origem:** 2.1
**Status:** Estrutura formalizada — endpoints detalhados serão preenchidos incrementalmente a partir da Sprint em que cada recurso for implementado.

---

## 1. Propósito deste documento

Este documento é a referência oficial de todos os endpoints HTTP expostos por `apps/api`. Ele existe desde a formalização estrutural do projeto (Sprint 2.1) para que toda nova rota criada seja documentada aqui no mesmo Pull Request que a introduz, conforme checklist de `DEVELOPMENT_CONVENTIONS.md`.

Nenhum endpoint entra em `develop` sem entrada correspondente neste documento.

---

## 2. Convenções gerais

Estas convenções são vinculantes para toda a API e detalhadas em `DEVELOPMENT_CONVENTIONS.md`, seção 9 e 10.

| Convenção | Regra |
|---|---|
| Prefixo de versão | `/api/v1/` |
| Formato de dados | `application/json` |
| Autenticação | Bearer Token (JWT), header `Authorization` |
| Paginação | Query params `limit` e `offset`, resposta com envelope `{ items, total, limit, offset }` |
| Erros | Envelope padronizado `{ error_code, message, details }` |
| Nomeação de recursos | Substantivos no plural (`/leads`, `/companies`) |
| Ações que não mapeiam para verbo HTTP | Sub-recurso (`/leads/{id}/approve`) |

### 2.1 Envelope padrão de erro

```json
{
  "error_code": "LEAD_NOT_FOUND",
  "message": "Lead não encontrado",
  "details": null
}
```

### 2.2 Códigos de status utilizados

| Código | Uso |
|---|---|
| `200` | Sucesso em operação de leitura ou atualização |
| `201` | Sucesso em criação de recurso |
| `204` | Sucesso sem corpo de resposta |
| `400` | Erro de validação de entrada |
| `401` | Autenticação ausente ou inválida |
| `403` | Autenticado, porém sem permissão para a ação |
| `404` | Recurso não encontrado |
| `409` | Conflito de estado (ex.: aprovar um lead já aprovado) |
| `422` | Corpo da requisição não processável pelo schema |
| `500` | Erro interno não tratado |

---

## 3. Domínios de recurso previstos

Esta seção lista os grupos de endpoints previstos para o projeto, na ordem em que aparecem no fluxo de negócio descrito em `ARCHITECTURE.md`. Cada grupo será detalhado (rota por rota, com request/response schema completo) no Pull Request correspondente à sua implementação.

| Recurso | Bounded Context | Status da documentação |
|---|---|---|
| `/api/v1/companies` | Prospecting | A detalhar na implementação |
| `/api/v1/leads` | Qualification / Scoring | A detalhar na implementação |
| `/api/v1/leads/{id}/approve` | Approval | A detalhar na implementação |
| `/api/v1/leads/{id}/reject` | Approval | A detalhar na implementação |
| `/api/v1/proposals` | Proposal | A detalhar na implementação |
| `/api/v1/outreach` | Outreach | A detalhar na implementação |
| `/api/v1/auth` | Autenticação e sessão | A detalhar na implementação |

A coluna "Status da documentação" é atualizada para "Documentado" apenas quando a seção correspondente abaixo (seção 4) for preenchida com o contrato completo do endpoint.

---

## 4. Endpoints

Nenhum endpoint foi implementado até o fechamento da Sprint 2.1. Esta seção é preenchida incrementalmente, um endpoint por vez, seguindo o template abaixo — nunca em lote e nunca antecipadamente à implementação real do código.

### 4.1 Template obrigatório por endpoint

```
### <MÉTODO> <rota>

**Bounded Context:** <contexto>
**Autenticação:** <obrigatória/pública>

**Request**
- Path params: ...
- Query params: ...
- Body (schema): ...

**Response — 200/201**
- Body (schema): ...

**Erros possíveis**
| Código | error_code | Quando ocorre |
|---|---|---|
```

---

## 5. Critérios de aceite deste documento

- [ ] Todo endpoint presente em `apps/api/src/leadhunter_api/presentation/api/v1/routers` possui entrada correspondente na seção 4.
- [ ] Nenhum Pull Request que adiciona ou altera uma rota é aprovado sem atualização deste documento.
- [ ] Os `error_code` documentados aqui correspondem exatamente às exceções de domínio tratadas pelo `exception_handler` central, descrito em `ARCHITECTURE.md`.
