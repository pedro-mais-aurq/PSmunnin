# PSmunnin — Overpass com três endpoints e uma rodada

Base: `PSmunnin-correcao (1).zip` fornecido nesta solicitação.
Esta revisão atualiza a documentação do comportamento vigente. O trabalho foi
feito no ZIP; não houve push, deploy nem alteração de variáveis do Render.

## Arquivos modificados ou criados

| Arquivo | Ação | Mudança |
| --- | --- | --- |
| `backend/server.py` | Modificado | Uma rodada, sem backoff, e resumo seguro de todas as falhas no log final. |
| `backend/overpass_config.py` | Criado | Endpoints, parsing, User-Agent e timeouts compartilhados com o diagnóstico, sem importar servidor/banco. |
| `backend/.env.example` | Modificado | Lista dos três endpoints na ordem solicitada. |
| `backend/tests/test_overpass.py` | Modificado | Testes adaptados à nova ordem, limite de chamadas e logs agregados. |
| `backend/tests/test_alpha_01.py` | Modificado | Uma expectativa desatualizada: `search_lang="pt"` passa a `"pt-br"`, conforme o código existente. |
| `backend/scripts/check_overpass.py` | Criado | Diagnóstico manual de conectividade por endpoint. |
| `backend/tests/test_check_overpass.py` | Criado | Testes do diagnóstico usando HTTP simulado, inclusive execução sem módulo do servidor. |
| `.github/workflows/backend-tests.yml` | Criado | CI Python 3.12, dependências locais de teste e `pytest -q`. |
| `README.md` | Modificado | Pool atual, uma rodada, configuração do Render, logs, CI e comando manual. |
| `docs/RELATORIO_CORRECAO_OVERPASS.md` | Modificado | Este relatório atualizado. |

Nenhum arquivo foi removido nesta revisão. Todo o frontend, inclusive favicon,
foi comparado byte a byte com o ZIP recebido e permanece idêntico.

## Pool final

1. `https://overpass.private.coffee/api/interpreter`
2. `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
3. `https://overpass-api.de/api/interpreter`

`OVERPASS_MAX_ROUNDS = 1`: no pool padrão são no máximo três chamadas, cada
endpoint uma vez, com retorno imediato no primeiro resultado válido. Foram
removidos a constante e o trecho de backoff. A numeração é `attempt=1`, `2`, `3`,
sempre com `round=1`. A diversidade adicional e a ausência de repetição reduzem
a espera quando os serviços estão indisponíveis; não garantem que um provedor
esteja acessível a partir do Render.

Os timeouts HTTPX continuam: conexão 10 s, leitura 45 s, escrita 10 s e pool 10 s.
O timeout interno da query de produção continua em 30 s. Limites por fase de I/O
não equivalem a um prazo máximo absoluto da pesquisa.

## Failover e observabilidade

São preservados o tratamento de `httpx.TransportError`, incluindo conexão,
timeouts, leitura, escrita e protocolo remoto, e a propagação de cancelamento.
HTTP 429/5xx, HTML, vazio, JSON inválido, `elements` inválido e `remark` de erro
continuam permitindo fallback. HTTP 400/401/403/404/422 continuam encerrando a
consulta com 502 controlado; não são mascarados como indisponibilidade.

Ao esgotar o pool, o log mantém o contexto da última tentativa, a causa técnica
e o campo `failures`, um JSON ordenado com somente endpoint, tipo de erro e
status HTTP quando existir. Por exemplo, o cenário de teste obrigatório produz:

```json
[
  {"endpoint": "https://overpass.private.coffee/api/interpreter", "error_type": "ReadTimeout"},
  {"endpoint": "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "error_type": "HTTPStatusError", "status": 503},
  {"endpoint": "https://overpass-api.de/api/interpreter", "error_type": "ConnectError"}
]
```

O log final mantém `search=<UUID>`, `attempt=3`, `round=1` e
`result=unavailable`. O resumo não contém corpo de resposta, headers ou tokens,
e não é enviado ao frontend. A mensagem persistida continua exatamente:

> Os serviços de coleta de empresas estão temporariamente indisponíveis. Tente novamente mais tarde.

O AST das 67 funções/classes fora da consulta e do parser movido foi comparado
com a base e permaneceu igual. Isso inclui pipeline, heartbeat, Nominatim,
scoring, detecção de sites, Brave, rotas e modelos da API. A mudança no teste
antigo da Brave alinha uma asserção ao valor já utilizado; não altera a integração
nem exclui, ignora ou enfraquece a verificação de localização brasileira.

## Validações executadas

Python 3.12.13. Dependências de `backend/requirements.local.txt` disponíveis em
ambiente virtual isolado.

| Comando/verificação | Resultado |
| --- | --- |
| `pytest -q` em `backend/` | Passou, código de saída 0. |
| `pytest -q -o addopts=''` em `backend/` | **140 passed, 1 skipped, 4 warnings** — nenhum teste falhou. |
| `pytest -q -o addopts='' tests/test_overpass.py tests/test_check_overpass.py` | **67 passed, 4 warnings**. |
| Ruff nos módulos e testes da coleta/diagnóstico | Passou. |
| Sintaxe YAML e estrutura do workflow | Válidas; eventos, paths, Python, diretório e comandos conferidos. |
| `python -m scripts.check_overpass --help` | Passou, sem chamadas de rede. |
| Comparação do frontend com o ZIP recebido | Todos os arquivos idênticos. |

O `-o addopts=''` apenas remove a opção `-q` duplicada de `pytest.ini` para
mostrar os totais; não seleciona nem ignora testes. O único teste ignorado é o
smoke opcional de MongoDB, que exige `RUN_MONGODB_INTEGRATION=1` e um serviço
configurado. Os quatro warnings são as deprecações preexistentes de
`FastAPI.on_event`, mantidas visíveis.

Os 67 testes de coleta e diagnóstico cobrem, entre outros, `ReadTimeout →`
segundo endpoint com sucesso, `ReadTimeout → HTTP 503 →` terceiro endpoint com
sucesso, e `ReadTimeout → HTTP 503 → ConnectError →` 503 amigável com resumo das
três falhas. Todos usam mocks. O diagnóstico real não foi executado nesta sessão.
Não foram repetidos builds do frontend, pois nenhum de seus arquivos mudou.

## CI

Criado `.github/workflows/backend-tests.yml`, que executa:

- em pushes para `correcao` com mudanças em `backend/**` ou no próprio workflow;
- em pull requests que alterem `backend/**` ou o workflow.

O job faz checkout, configura Python 3.12, instala `requirements.local.txt` e
executa `pytest -q` dentro de `backend/`. Uma falha de teste falha o job, sem
`continue-on-error`. A integração opcional MongoDB fica desativada. O diagnóstico
real não é chamado no CI.

O workflow foi validado localmente, mas ainda não executado no GitHub. Ele não
configura sozinho uma trava de deploy no Render: checks obrigatórios e a política
de deploy devem ser configurados no serviço/repositório, se desejado.

## Diagnóstico manual no Render Shell

Com a raiz do serviço definida como `backend/`:

```bash
python -m scripts.check_overpass
```

Se o shell abrir na raiz do repositório, execute primeiro `cd backend`.
O script consulta no máximo um elemento OSM por endpoint, individualmente e
sem repetir, mesmo quando um endpoint anterior funciona. Usa os mesmos
endpoints, User-Agent e timeouts HTTPX da aplicação. Não importa o pipeline,
não exige credenciais MongoDB e não modifica banco de dados. Exibe status,
resultado e tempo aproximado. Código de saída: 0 se todos responderem com JSON
válido; 1 se qualquer endpoint falhar. Execute sob demanda, fora do CI.

## Configuração importante no Render

Se `OVERPASS_ENDPOINTS` já estiver definida, ela sobrescreve o novo pool padrão.
Após publicar o código, atualize-a manualmente para:

```env
OVERPASS_ENDPOINTS=https://overpass.private.coffee/api/interpreter,https://maps.mail.ru/osm/tools/overpass/api/interpreter,https://overpass-api.de/api/interpreter
```

Ou remova essa variável para usar os defaults. Nenhuma variável real foi
alterada ou incluída na entrega. O ZIP não inclui `.env` real, ambiente virtual,
`node_modules`, caches ou artefatos de build.
