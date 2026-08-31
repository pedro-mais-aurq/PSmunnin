# PSmunnin — correção de coleta Overpass e favicon

Data: 31/08/2026. Base: arquivo `PSmunnin-correcao.zip` fornecido, correspondente
à branch `correcao` e ao commit de origem
`746253bb09cdc9d4f4d4cb24dc306bb4b56898a1` indicado no ZIP.

As alterações foram aplicadas à cópia anexada. Não houve push ao GitHub, deploy,
alteração de variáveis de produção ou uso de credenciais reais.

## Arquivos alterados

| Arquivo | Ação | Alteração |
| --- | --- | --- |
| `backend/server.py` | Modificado | Pool, parsing de configuração, `query_overpass`, timeouts, failover, validação, logs, propagação de `search_id` e erros amigáveis. |
| `backend/.env.example` | Modificado | `OVERPASS_ENDPOINTS` e User-Agent identificável. |
| `backend/tests/test_overpass.py` | Criado | 52 casos executados, incluindo variações parametrizadas e regressões do pipeline. |
| `frontend/src/lib/api.ts` | Modificado | Classificação dos erros HTTP e de transporte que permitem repetir o polling. |
| `frontend/src/app/components/DashboardClient.tsx` | Modificado | Interrompe repetição em erros permanentes da consulta HTTP; mantém a lógica dos estados. |
| `frontend/src/test/api.test.mjs` | Criado | 16 testes com `fetch` simulado, sem dependências novas. |
| `frontend/src/app/layout.tsx` | Modificado | Remove configuração manual redundante de `icons`. |
| `frontend/src/app/icon.svg` | Criado | Cópia exata do logo existente para a convenção do App Router. |
| `frontend/public/favicon.ico` | Removido | Era XML/SVG com extensão ICO incorreta. |
| `README.md` | Modificado | Configuração, comportamento, diagnóstico e comandos de testes. |
| `docs/RELATORIO_CORRECAO_OVERPASS.md` | Criado | Este relatório. |

`frontend/public/psmunnin-logo.svg`, `package.json`, `package-lock.json`, os
contratos da API e os testes antigos foram preservados.

## Mudanças realizadas

- Pool padrão: Private Coffee → overpass-api.de. `OVERPASS_ENDPOINTS` substitui
  a lista; parsing remove espaços, vazios e duplicatas. Variável ausente usa
  os defaults; lista explicitamente vazia é erro de configuração. URLs não
  podem conter credenciais, query string ou fragmento.
- `query_overpass()` concentra a integração HTTP. São no máximo duas rodadas
  pelo pool, com uma espera assíncrona de 1,5 segundo entre elas. Nenhum
  `time.sleep()` foi introduzido.
- Timeouts por fase: conexão 10 s, leitura 45 s, escrita 10 s e pool 10 s.
  Eles não constituem um limite total de duração da pesquisa.
- Falhas de transporte, HTTP 429/5xx e respostas inválidas acionam failover.
  Outros 4xx interrompem a coleta com uma mensagem de rejeição identificável
  (exceção controlada 502). Redirecionamentos inesperados também não são
  percorridos silenciosamente.
- JSON precisa ser um objeto com `elements` como lista de objetos. `elements=[]`
  é válido. HTML, vazio, estruturas inesperadas e respostas com `remark`
  indicando falha de execução são recusados, permitindo fallback.
- Logs incluem o UUID da pesquisa, provedor, endpoint, tentativa global,
  rodada e resultado. Status e tipo da exceção aparecem quando aplicáveis.
  Trechos de respostas rejeitadas ficam limitados a cabeçalhos conhecidos de
  diagnóstico, como `line 4: parse error`, sem copiar queries ou corpo arbitrário.
- Ao esgotar o pool, a exceção 503 mantém a causa técnica para diagnóstico;
  o pipeline persiste `failed` com a mensagem: “Os serviços de coleta de empresas
  estão temporariamente indisponíveis. Tente novamente mais tarde.”
- Erros inesperados também deixam de expor nomes de classes ao usuário.
  O traceback continua nos logs. O fluxo `running → coleta → análise →
  persistência → done/failed` e o encerramento do heartbeat foram preservados.
- `total_found` só é atualizado após uma coleta válida. Testes verificam que
  falha definitiva não inicia a análise nem altera leads, e que o heartbeat
  continua durante o backoff.
- Polling continua em `pending`/`running` e para em `done`/`failed`, exibindo
  `search.error`. Repetições da requisição HTTP ficam limitadas a erros de rede,
  timeout e HTTP 408/429/5xx. Erros permanentes, configuração ausente e erros
  de programação fora da camada HTTP não geram repetição.
- Favicon nativo em `src/app/icon.svg`, sem redesenho. O Next.js gera a metadata
  e respeita o `basePath=/PSmunnin`.

Os códigos 502/503 acima descrevem exceções internas controladas da coleta,
não uma mudança no contrato de polling: a criação continua com HTTP 202 e a
consulta de uma pesquisa existente continua com HTTP 200 e seu estado persistido.

## Validação executada

Ambiente: Python 3.12.13, Node.js 24.19.0, npm 11.9.0, Next.js 15.5.22.
Dependências Python instaladas de `backend/requirements.local.txt` em ambiente
virtual isolado. `npm install` executado em `frontend/`, sem alterar o lockfile.

| Validação | Resultado real |
| --- | --- |
| `pytest -q -o addopts=''` em `backend/` | **124 passaram, 1 falhou, 1 ignorado**, 4 warnings. |
| `pytest -q -o addopts='' tests/test_overpass.py` | **52 passaram**, 4 warnings preexistentes. |
| `node --test src/test/api.test.mjs` em `frontend/` | **16 passaram**. |
| `npm run check` em `frontend/` | **Passou**: tipos e ESLint. |
| `npm run build` em `frontend/` | **Passou**: exportação estática, incluindo rota `/icon.svg`. |
| Build com `NEXT_PUBLIC_BASE_PATH=/PSmunnin` | **Passou**, metadata aponta para `/PSmunnin/icon.svg?...`. |
| Ruff em `server.py` e `tests/test_overpass.py` | **Passou**. |
| Favicon exportado em servidor HTTP local | **HTTP 200**, MIME `image/svg+xml`. |
| SVG do favicon | XML válido, autocontido e idêntico byte a byte ao logo existente. |
| Comparação da função Brave e do heartbeat com o ZIP original | Implementações inalteradas. |

Todos os testes adicionados usam mocks; não consultam Overpass, Nominatim,
Brave ou MongoDB reais.

## Falha preexistente reproduzida

A suíte completa não está inteiramente verde. O teste
`tests/test_alpha_01.py::test_brave_search_uses_brazilian_localization`, linha
1351 do arquivo original, espera `search_lang="pt"`, mas a implementação
original envia `"pt-br"`:

```text
assert request.url.params["search_lang"] == "pt"
AssertionError: assert 'pt-br' == 'pt'
```

Para confirmar a origem, o ZIP foi extraído novamente em um diretório separado,
sem aplicar o patch, e esse teste foi executado isoladamente. Resultado:
`1 failed, 4 warnings`. A função `search_web_for_website()` também foi comparada
por AST com a original e permanece idêntica. Não foi modificada a Brave nem
enfraquecido o teste para aparentar sucesso. Essa divergência exige uma decisão
separada, conforme o escopo solicitado.

O teste ignorado é `test_mongodb_connection_smoke`: exige
`RUN_MONGODB_INTEGRATION=1` e uma instância MongoDB configurada explicitamente.
Os quatro warnings Python são deprecações de `FastAPI.on_event`, presentes na
versão original. Não foram suprimidos. O npm também informa um aviso de
configuração `http-proxy` do ambiente; ele não impediu tipos, lint ou build.

## Limitações e preservações

- O navegador disponibilizado no ambiente bloqueou a abertura do endereço local
  com `ERR_BLOCKED_BY_CLIENT`. Por isso, não se afirma validação visual em browser
  nem teste completo da interface em execução. A verificação do favicon foi
  feita sobre o HTML exportado, o SVG e a resposta HTTP local. O encerramento do
  polling foi revisado no código; os testes de frontend validam a camada HTTP.
- Não houve teste de disponibilidade real das instâncias públicas nem execução
  completa em Render/MongoDB. Os testes reproduzem as falhas por HTTP simulado.
- `M_ID` não foi encontrado no código-fonte fornecido. Não foi criado workaround.
  Sua origem não foi confirmada; pode estar em bundle, runtime ou extensão.
- Nominatim não foi tratado como a causa principal. Sua chamada foi preservada;
  apenas recebeu logs de contexto na etapa de coleta.
- Não foram adicionados Tavily, Exa ou Serper. A integração Brave foi preservada.
- Endpoints e formatos de `Search`, `SearchDetail` e `Lead` permanecem compatíveis.
- O ZIP de entrega contém código e documentação, sem `.env` real, credenciais,
  ambiente virtual, `node_modules`, caches ou artefatos de build.

Após publicar o patch, uma pesquisa real pode ser acompanhada no Render pelo
UUID para confirmar a conectividade do ambiente de produção e o failover.
