# PS Munnin — PRD

## Original Problem Statement
Sistema chamado PS Munnin para automatizar prospecção de clientes para desenvolvedores web. Usuário informa nicho + região, sistema coleta empresas, analisa presença digital (site, HTTPS, SEO, performance), calcula score de prioridade e apresenta melhores oportunidades. Usuário vê leads em painel, analisa dados e gera contato personalizado. Foco: MVP funcional, não SaaS completo.

## Arquitetura
- **Backend**: FastAPI + Motor (MongoDB async) + httpx. Endpoints em `/api/*`. Pipeline assíncrono em background.
- **Frontend**: React 19 + React Router + Tailwind + shadcn/ui + axios.
- **Fontes de dados** (grátis, sem chave):
  - Nominatim (geocode da região → bbox)
  - Overpass API (POIs OSM por bbox + filtros por nicho)
- **Análise de site**: httpx GET com heurísticas regex (HTTPS, `<title>`, meta description, meta viewport, favicon, response time, status HTTP).
- **Score (0-100)**: quanto pior a presença digital, maior o score. `high >=75`, `medium >=50`, `low <50`.
- **Mensagens**: templates fixos (email/whatsapp) preenchidos com nome + issues detectadas.
- **Sem autenticação** (single-user).

## Personas
- Desenvolvedor web freelancer buscando novos clientes por nicho local.

## Requisitos MVP (todos implementados)
- [x] Cadastrar pesquisa (nicho + região + limit)
- [x] Executar fluxo principal (Overpass → análise → score) em background
- [x] Visualizar lista de pesquisas com status (pending/running/done/failed)
- [x] Visualizar leads ordenados por score
- [x] Ver detalhes de cada lead com métricas e issues
- [x] Gerar sugestão de contato (email ou whatsapp)
- [x] Copiar mensagem para clipboard
- [x] Filtrar leads por prioridade
- [x] Excluir pesquisas

## Arquivos alterados/criados
### Backend
- `/app/backend/server.py` — reescrito com endpoints, modelos, pipeline, análise de site, scoring, templates de mensagem
- `/app/backend/requirements.txt` — adicionado `httpx>=0.28`

### Frontend
- `/app/frontend/src/App.js` — rotas do MVP
- `/app/frontend/src/App.css` — tema dark + scrollbar
- `/app/frontend/src/lib/api.js` — cliente axios centralizado (novo)
- `/app/frontend/src/components/Layout.jsx` — header + nav (novo)
- `/app/frontend/src/components/Badges.jsx` — ScorePill, StatusBadge, PriorityBadge (novo)
- `/app/frontend/src/pages/Dashboard.jsx` — lista de pesquisas (novo)
- `/app/frontend/src/pages/NewSearch.jsx` — formulário de nova pesquisa (novo)
- `/app/frontend/src/pages/SearchDetail.jsx` — detalhes da pesquisa + leads (novo)
- `/app/frontend/src/pages/LeadDetail.jsx` — detalhes do lead + gerador de mensagem (novo)
- `/app/frontend/src/constants/testIds/psm.js` — test IDs (novo)
- `/app/frontend/src/constants/testIds/index.js` — inclui psm

## Status de testes
- Backend: 100% (health, CRUD searches, pipeline, leads, mensagens email/whatsapp, erro de região)
- Frontend: 100% (dashboard, nova pesquisa, detalhes, lead, geração de mensagem, cópia)

## Backlog (P1/P2)
- P1: paginação e busca dentro de uma pesquisa
- P1: exportar leads (CSV)
- P1: análise mais profunda (Lighthouse via API opcional)
- P2: multi-user / autenticação
- P2: agendar re-análise periódica
- P2: integração com WhatsApp Business para envio direto
