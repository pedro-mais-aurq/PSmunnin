# PS Munnin — PRD do MVP

## Problema

O PS Munnin reduz o trabalho manual de localizar empresas locais com baixa
maturidade digital e organizar oportunidades de prospecção para serviços de
desenvolvimento web.

## Usuário

O MVP atende um único operador: desenvolvedor web ou freelancer responsável por
executar pesquisas e revisar os leads encontrados.

## Fluxo

1. O operador informa nicho, região e limite de resultados.
2. O frontend envia a pesquisa ao FastAPI.
3. O backend geocodifica a região com Nominatim.
4. O backend consulta empresas no OpenStreetMap pela Overpass API.
5. Os websites encontrados são analisados.
6. Cada empresa recebe score e prioridade.
7. Os resultados são persistidos no MongoDB.
8. O frontend consulta o andamento da pesquisa.
9. O operador revisa os leads.
10. O operador gera e copia uma mensagem de contato.

## Arquitetura atual

- Frontend: Next.js, React e TypeScript.
- Hospedagem do frontend: GitHub Pages.
- Backend: FastAPI, Motor, MongoDB e HTTPX.
- Hospedagem do backend: Render.
- Dados externos: Nominatim e Overpass API.
- Processamento assíncrono: tarefa no mesmo processo FastAPI.
- Autenticação: não implementada no MVP.
- Envio automático de mensagens: não implementado.

## Endpoints

- `GET /api/`
- `GET /api/health`
- `POST /api/searches`
- `GET /api/searches`
- `GET /api/searches/{search_id}`
- `DELETE /api/searches/{search_id}`
- `GET /api/leads/{lead_id}`
- `GET /api/leads/{lead_id}/message`

## Limitações conhecidas

- Pesquisas ativas mantêm heartbeat. Desligamentos normais falham somente as
  tarefas pertencentes à instância encerrada; registros sem heartbeat recente
  são recuperados pelo monitor de pesquisas obsoletas.
- O sistema depende da disponibilidade do OpenStreetMap, Nominatim e Overpass.
- O MVP não possui autenticação ou multiusuário.
- Mensagens são geradas para revisão e cópia manual.
