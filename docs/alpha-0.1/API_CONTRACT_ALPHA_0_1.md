# PS Munnin — Contrato de API da Alpha 0.1

**Arquivo normativo:** `docs/alpha-0.1/API_CONTRACT_ALPHA_0_1.md`  
**Versão do contrato:** `alpha-0.1`  
**Status:** congelado para implementação  
**Base de código:** `PSmunnin-hotfix-recuperacao-final.zip`  
**SHA-256 da base:** `8caafb179aef4fe108b23df9f97b165df132182d6e2840d00316cf95760fce9a`  
**Especificação de origem:** `PSMUNNIN_ALPHA_0_1_GUIA_IMPLEMENTACAO.md`

---

## 1. Finalidade

Este documento define o contrato REST/JSON compartilhado entre o backend e o frontend do PS Munnin Alpha 0.1.

Ele é a fonte normativa para:

- modelos de entrada e saída da API;
- nomes e tipos dos campos;
- semântica da detecção de website;
- estrutura dos contatos coletados;
- compatibilidade com registros anteriores;
- consumo dos dados pelo frontend;
- testes de contrato e integração.

Nenhuma LLM programadora pode renomear, remover ou reinterpretar unilateralmente os campos definidos aqui.

---

## 2. Regras de compatibilidade

A Alpha 0.1 é uma alteração **aditiva**.

São regras obrigatórias:

1. Todos os endpoints existentes permanecem com os mesmos caminhos e métodos HTTP.
2. Todos os campos já existentes permanecem com os mesmos nomes e tipos.
3. Os novos campos são adicionados ao modelo `Lead`.
4. Não é criada nova versão de rota, como `/api/v2`.
5. Não é criada migration obrigatória do MongoDB.
6. Documentos antigos devem ser aceitos por `_deserialize_lead`.
7. O frontend deve continuar funcionando quando receber um registro antigo sem os novos campos persistidos.
8. Ausência de tag de website no OpenStreetMap não pode ser interpretada automaticamente como ausência confirmada de site.
9. `website_reachable` representa acessibilidade; não representa existência.
10. O website oficial permanece no campo `website`; ele não é duplicado dentro de `contacts`.

---

## 3. Base URL

O frontend monta a URL da API a partir de:

```text
NEXT_PUBLIC_API_URL + "/api"
```

Exemplo lógico:

```text
https://backend.exemplo.com/api
```

Todos os caminhos deste contrato são relativos ao prefixo `/api`.

---

## 4. Tipos enumerados

### 4.1 `SearchStatus`

```text
pending | running | done | failed
```

### 4.2 `LeadPriority`

```text
low | medium | high
```

### 4.3 `ContactChannel`

```text
email | whatsapp | generic
```

### 4.4 `WebsiteDetectionStatus`

```text
confirmed | not_found | unknown
```

Semântica:

| Valor | Significado normativo |
|---|---|
| `confirmed` | Um website oficial foi identificado com evidência suficiente. O site continua confirmado mesmo quando estiver inacessível. |
| `not_found` | Todas as etapas de descoberta configuradas e disponíveis foram concluídas sem encontrar candidato confiável. |
| `unknown` | As fontes disponíveis não permitiram concluir. Inclui busca externa desabilitada, indisponível ou com falha. |

### 4.5 `WebsiteSource`

```text
osm_website | osm_contact_website | osm_url | email_domain | web_search
```

Semântica:

| Valor | Origem |
|---|---|
| `osm_website` | Tag `website` do OpenStreetMap. |
| `osm_contact_website` | Tag `contact:website` do OpenStreetMap. |
| `osm_url` | Tag `url` do OpenStreetMap, após validação como website oficial. |
| `email_domain` | Domínio corporativo derivado de e-mail coletado e confirmado por HTTP. |
| `web_search` | Resultado confiável de descoberta web opcional e confirmado. |

---

## 5. Modelos de dados

## 5.1 `SearchCreate`

Corpo de `POST /searches`.

```typescript
export type SearchCreate = {
  nicho: string;
  regiao: string;
  limit: number;
};
```

Regras:

| Campo | Tipo | Obrigatório | Restrições |
|---|---|---:|---|
| `nicho` | `string` | Sim | Entre 2 e 80 caracteres após `trim`. |
| `regiao` | `string` | Sim | Entre 2 e 120 caracteres após `trim`. |
| `limit` | `number` inteiro | Sim no frontend; possui padrão no backend | Entre 1 e 60. Padrão do backend: `25`. |

Exemplo:

```json
{
  "nicho": "salões de beleza",
  "regiao": "Belo Horizonte, MG",
  "limit": 25
}
```

---

## 5.2 `Search`

```typescript
export type Search = {
  id: string;
  nicho: string;
  regiao: string;
  status: SearchStatus;
  total_found: number;
  total_analyzed: number;
  error: string | null;
  created_at: string;
  updated_at: string;
};
```

Formato temporal: string ISO 8601.

Exemplo:

```json
{
  "id": "a6dc9ae4-e7c9-45a1-9878-109cbac4d4fd",
  "nicho": "salões de beleza",
  "regiao": "Belo Horizonte, MG",
  "status": "running",
  "total_found": 18,
  "total_analyzed": 7,
  "error": null,
  "created_at": "2026-07-31T21:00:00+00:00",
  "updated_at": "2026-07-31T21:00:12+00:00"
}
```

---

## 5.3 `ContactInfo`

Objeto adicionado ao `Lead`.

```typescript
export type ContactInfo = {
  phone: string[];
  mobile: string[];
  whatsapp: string[];
  email: string[];
  instagram: string[];
  facebook: string[];
  linkedin: string[];
};
```

Equivalente esperado no backend:

```python
class ContactInfo(BaseModel):
    phone: list[str] = Field(default_factory=list)
    mobile: list[str] = Field(default_factory=list)
    whatsapp: list[str] = Field(default_factory=list)
    email: list[str] = Field(default_factory=list)
    instagram: list[str] = Field(default_factory=list)
    facebook: list[str] = Field(default_factory=list)
    linkedin: list[str] = Field(default_factory=list)
```

### Regras de normalização

1. Valores vazios são ignorados.
2. Valores múltiplos separados por `;` são divididos.
3. Espaços excedentes são removidos.
4. Duplicatas são eliminadas preservando a ordem original.
5. Telefones, celulares e WhatsApp permanecem como texto.
6. Usernames sociais são convertidos em URLs completas.
7. URLs sociais completas válidas são mantidas e normalizadas.
8. A extração de contatos não realiza chamadas externas.
9. O website oficial não integra este objeto; permanece em `website`.

### Tags OSM aceitas

| Campo do contrato | Tags aceitas |
|---|---|
| `phone` | `phone`, `contact:phone` |
| `mobile` | `mobile`, `contact:mobile` |
| `whatsapp` | `whatsapp`, `contact:whatsapp` |
| `email` | `email`, `contact:email` |
| `instagram` | `instagram`, `contact:instagram` |
| `facebook` | `facebook`, `contact:facebook` |
| `linkedin` | `linkedin`, `contact:linkedin` |

Exemplo:

```json
{
  "phone": ["+55 31 3333-4444"],
  "mobile": ["+55 31 98888-7777"],
  "whatsapp": ["+55 31 98888-7777"],
  "email": ["contato@empresa.com.br"],
  "instagram": ["https://www.instagram.com/empresa/"],
  "facebook": ["https://www.facebook.com/empresa"],
  "linkedin": []
}
```

---

## 5.4 `Lead`

Contrato completo da Alpha 0.1:

```typescript
export type Lead = {
  id: string;
  search_id: string;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  lat: number | null;
  lon: number | null;
  has_website: boolean;
  website_reachable: boolean | null;
  https: boolean | null;
  response_ms: number | null;
  has_title: boolean | null;
  has_meta_description: boolean | null;
  has_viewport: boolean | null;
  has_favicon: boolean | null;
  status_code: number | null;
  issues: string[];
  score: number;
  priority: LeadPriority;
  created_at: string;

  contacts: ContactInfo;
  website_status: WebsiteDetectionStatus;
  website_source: string | null;
};
```

### Campos adicionados na Alpha 0.1

| Campo | Tipo | Valor padrão do backend |
|---|---|---|
| `contacts` | `ContactInfo` | Objeto com todas as listas vazias. |
| `website_status` | `WebsiteDetectionStatus` | `unknown` |
| `website_source` | `string \| null` (valores de `WebsiteSource`) | `null` |

### Campos antigos preservados

Os campos abaixo não podem ser removidos nem renomeados:

```text
phone
website
has_website
website_reachable
```

### Regras de coerência

| `website_status` | `website` | `has_website` | `website_reachable` | `website_source` |
|---|---|---:|---|---|
| `confirmed` | URL oficial escolhida | `true` | `true` ou `false` | Um valor de `WebsiteSource` |
| `not_found` | `null` | `false` | `null` | `null` |
| `unknown` | `null` | `false` | `null` | `null` |

Regras adicionais:

1. Website declarado no OSM permanece `confirmed` quando estiver inacessível.
2. Nesse caso, `has_website=true` e `website_reachable=false`.
3. Perfil social ou agregador nunca pode preencher `website` nem produzir `confirmed`.
4. URL social encontrada em campo de website deve ser incorporada ao canal correspondente em `contacts` e a busca por website oficial deve continuar.
5. `phone` contém o primeiro valor disponível nesta ordem operacional: telefone, celular ou WhatsApp.
6. `contacts.phone` contém todos os telefones normalizados especificamente das tags de telefone.
7. `issues` não deve expor nome de exceção técnica ao usuário.
8. Detalhes técnicos de falha permanecem somente nos logs do backend.

### Mensagens funcionais esperadas em `issues`

Conforme o resultado, o backend pode usar as mensagens:

```text
Site cadastrado, mas inacessível
Verificação do site expirou
Site não encontrado nas fontes consultadas
Verificação de site inconclusiva
```

O texto absoluto `Sem site cadastrado` não deve ser usado como conclusão da Alpha 0.1.

### Exemplo A — site confirmado e acessível

```json
{
  "id": "lead-001",
  "search_id": "search-001",
  "name": "Studio Exemplo",
  "category": "beauty_salon",
  "address": "Rua Exemplo, 100, Belo Horizonte",
  "phone": "+55 31 3333-4444",
  "website": "https://studioexemplo.com.br",
  "lat": -19.9191,
  "lon": -43.9386,
  "has_website": true,
  "website_reachable": true,
  "https": true,
  "response_ms": 640,
  "has_title": true,
  "has_meta_description": false,
  "has_viewport": true,
  "has_favicon": true,
  "status_code": 200,
  "issues": ["Meta description ausente"],
  "score": 35,
  "priority": "low",
  "created_at": "2026-07-31T21:02:00+00:00",
  "contacts": {
    "phone": ["+55 31 3333-4444"],
    "mobile": [],
    "whatsapp": ["+55 31 99999-8888"],
    "email": ["contato@studioexemplo.com.br"],
    "instagram": ["https://www.instagram.com/studioexemplo/"],
    "facebook": [],
    "linkedin": []
  },
  "website_status": "confirmed",
  "website_source": "osm_website"
}
```

### Exemplo B — website declarado, porém inacessível

```json
{
  "id": "lead-002",
  "search_id": "search-001",
  "name": "Empresa com Site Offline",
  "category": null,
  "address": null,
  "phone": null,
  "website": "https://empresa-offline.example",
  "lat": null,
  "lon": null,
  "has_website": true,
  "website_reachable": false,
  "https": true,
  "response_ms": null,
  "has_title": null,
  "has_meta_description": null,
  "has_viewport": null,
  "has_favicon": null,
  "status_code": null,
  "issues": ["Site cadastrado, mas inacessível"],
  "score": 65,
  "priority": "medium",
  "created_at": "2026-07-31T21:03:00+00:00",
  "contacts": {
    "phone": [],
    "mobile": [],
    "whatsapp": [],
    "email": [],
    "instagram": [],
    "facebook": [],
    "linkedin": []
  },
  "website_status": "confirmed",
  "website_source": "osm_contact_website"
}
```

> O valor `65` reflete a fórmula publicada: base `25` acrescida de `40` para site quebrado ou inacessível.

### Exemplo C — site não encontrado de forma conclusiva

```json
{
  "id": "lead-003",
  "search_id": "search-001",
  "name": "Empresa sem Site Encontrado",
  "category": null,
  "address": "Belo Horizonte, MG",
  "phone": "+55 31 98888-7777",
  "website": null,
  "lat": null,
  "lon": null,
  "has_website": false,
  "website_reachable": null,
  "https": null,
  "response_ms": null,
  "has_title": null,
  "has_meta_description": null,
  "has_viewport": null,
  "has_favicon": null,
  "status_code": null,
  "issues": ["Site não encontrado nas fontes consultadas"],
  "score": 92,
  "priority": "high",
  "created_at": "2026-07-31T21:04:00+00:00",
  "contacts": {
    "phone": [],
    "mobile": ["+55 31 98888-7777"],
    "whatsapp": [],
    "email": [],
    "instagram": ["https://www.instagram.com/empresa/"],
    "facebook": [],
    "linkedin": []
  },
  "website_status": "not_found",
  "website_source": null
}
```

### Exemplo D — verificação inconclusiva

```json
{
  "id": "lead-004",
  "search_id": "search-001",
  "name": "Empresa com Verificação Inconclusiva",
  "category": null,
  "address": "Belo Horizonte, MG",
  "phone": null,
  "website": null,
  "lat": null,
  "lon": null,
  "has_website": false,
  "website_reachable": null,
  "https": null,
  "response_ms": null,
  "has_title": null,
  "has_meta_description": null,
  "has_viewport": null,
  "has_favicon": null,
  "status_code": null,
  "issues": ["Verificação de site inconclusiva"],
  "score": 50,
  "priority": "medium",
  "created_at": "2026-07-31T21:05:00+00:00",
  "contacts": {
    "phone": [],
    "mobile": [],
    "whatsapp": [],
    "email": [],
    "instagram": [],
    "facebook": [],
    "linkedin": []
  },
  "website_status": "unknown",
  "website_source": null
}
```

---

## 5.5 `SearchDetail`

Resposta de `GET /searches/{search_id}`.

```typescript
export type SearchDetail = {
  search: Search;
  leads: Lead[];
};
```

Exemplo reduzido:

```json
{
  "search": {
    "id": "search-001",
    "nicho": "salões de beleza",
    "regiao": "Belo Horizonte, MG",
    "status": "done",
    "total_found": 4,
    "total_analyzed": 4,
    "error": null,
    "created_at": "2026-07-31T21:00:00+00:00",
    "updated_at": "2026-07-31T21:06:00+00:00"
  },
  "leads": []
}
```

Os leads devem continuar ordenados pelo backend por `score` decrescente.

---

## 5.6 `ContactMessage`

```typescript
export type ContactMessage = {
  subject: string;
  body: string;
  channel: "email" | "whatsapp" | "generic";
};
```

A Alpha 0.1 não implementa envio. Este objeto permanece uma prévia de mensagem manual.

---

## 6. Endpoints congelados

## 6.1 `GET /`

Resposta `200`:

```json
{
  "service": "PS Munnin API",
  "status": "ok"
}
```

---

## 6.2 `GET /health`

Resposta `200`:

```json
{
  "status": "ok"
}
```

Resposta `503` quando o MongoDB estiver indisponível:

```json
{
  "detail": "Banco de dados indisponível."
}
```

---

## 6.3 `POST /searches`

Cria pesquisa e inicia o pipeline assíncrono atual.

Corpo: `SearchCreate`.

Resposta `202`: `Search`.

Nenhum novo endpoint deve substituir esta operação.

---

## 6.4 `GET /searches`

Resposta `200`:

```typescript
Search[]
```

Permanece limitado pelo backend aos 200 documentos mais recentes.

---

## 6.5 `GET /searches/{search_id}`

Resposta `200`: `SearchDetail`.

Resposta `404`:

```json
{
  "detail": "Pesquisa não encontrada."
}
```

Este endpoint permanece sendo a fonte do polling do frontend.

---

## 6.6 `DELETE /searches/{search_id}`

Resposta `200`:

```json
{
  "ok": true
}
```

Resposta `404`:

```json
{
  "detail": "Pesquisa não encontrada."
}
```

A remoção continua excluindo a pesquisa e seus leads relacionados.

---

## 6.7 `GET /leads/{lead_id}`

Resposta `200`: `Lead` da Alpha 0.1.

Resposta `404`:

```json
{
  "detail": "Lead não encontrado."
}
```

---

## 6.8 `GET /leads/{lead_id}/message`

Query opcional:

```text
channel=email | whatsapp | generic
```

Valor padrão:

```text
email
```

Resposta `200`: `ContactMessage`.

Resposta `404`:

```json
{
  "detail": "Lead não encontrado."
}
```

A funcionalidade continua sendo somente geração de texto; não envia mensagem.

---

## 7. Matriz normativa da detecção de website

| Situação | `website_status` | `website_source` | `website` | `has_website` | `website_reachable` |
|---|---|---|---|---:|---|
| Tag `website` contém site oficial | `confirmed` | `osm_website` | URL escolhida | `true` | Resultado da análise HTTP |
| Tag `contact:website` contém site oficial | `confirmed` | `osm_contact_website` | URL escolhida | `true` | Resultado da análise HTTP |
| Tag `url` contém site oficial | `confirmed` | `osm_url` | URL escolhida | `true` | Resultado da análise HTTP |
| URL declarada existe, mas está fora do ar | `confirmed` | Fonte OSM correspondente | URL escolhida | `true` | `false` |
| Domínio corporativo do e-mail foi confirmado | `confirmed` | `email_domain` | URL confirmada | `true` | `true` |
| Busca opcional encontrou resultado confiável | `confirmed` | `web_search` | URL confirmada | `true` | `true` |
| Todas as camadas habilitadas terminaram sem resultado | `not_found` | `null` | `null` | `false` | `null` |
| Busca externa desabilitada sem outra evidência | `unknown` | `null` | `null` | `false` | `null` |
| Chave da busca ausente sem outra evidência | `unknown` | `null` | `null` | `false` | `null` |
| Busca externa falhou sem outra evidência | `unknown` | `null` | `null` | `false` | `null` |
| Campo `website` contém somente Instagram/Facebook/agregador | Continuar descoberta | `null` até confirmação | `null` | `false` | `null` |

---

## 8. Regras do score relacionadas ao contrato

A fórmula geral existente permanece inalterada.

Somente estas regras são normativas para a Alpha 0.1:

| Condição | Tratamento |
|---|---|
| `website_status="confirmed"` e `website_reachable=true` | Aplicar cálculo atual de site existente. |
| `website_status="confirmed"` e `website_reachable=false` | Aplicar cálculo atual de site quebrado/inacessível. |
| `website_status="not_found"` | `score=92` e prioridade alta, conforme comportamento atual conclusivo. |
| `website_status="unknown"` | `score=50` e `priority="medium"`; nunca aplicar 92. |

A passagem de alguns leads de prioridade alta para média após a correção é comportamento esperado.

---

## 9. Compatibilidade com documentos antigos

`_deserialize_lead` deve aceitar documentos MongoDB sem `contacts`, `website_status` e `website_source`.

### 9.1 Valores padrão

Quando `contacts` não existir:

```json
{
  "phone": [],
  "mobile": [],
  "whatsapp": [],
  "email": [],
  "instagram": [],
  "facebook": [],
  "linkedin": []
}
```

Quando `website_source` não existir:

```text
null
```

### 9.2 Inferência de `website_status` em registros antigos

Aplicar exatamente:

```text
website preenchido + website_reachable=false → confirmed
website preenchido → confirmed
website vazio → unknown
```

Registros antigos sem website nunca devem ser convertidos automaticamente para `not_found`.

Não é necessária migration física do MongoDB.

---

## 10. Contrato defensivo do frontend

O frontend deve declarar os novos tipos conforme a seção 5, mas tratar registros antigos em runtime.

Fallback obrigatório:

```typescript
const contacts = lead.contacts ?? {
  phone: lead.phone ? [lead.phone] : [],
  mobile: [],
  whatsapp: [],
  email: [],
  instagram: [],
  facebook: [],
  linkedin: [],
};
```

Fallback de status para dado antigo:

```typescript
const websiteStatus =
  lead.website_status
  ?? (lead.website ? "confirmed" : "unknown");
```

O frontend não pode:

- contar `unknown` como “site não encontrado”;
- inferir `not_found` a partir de `!has_website`;
- renomear campos do backend;
- criar novo endpoint;
- alterar `apiRequest` para acomodar o novo contrato;
- implementar envio de mensagens.

---

## 11. Apresentação normativa no dashboard

### 11.1 Textos de status

| Condição | Texto exibido |
|---|---|
| `confirmed` e acessível | `Site confirmado` |
| `confirmed` e inacessível | `Site cadastrado, inacessível` |
| `not_found` | `Site não encontrado` |
| `unknown` | `Verificação inconclusiva` |

### 11.2 Métricas

O dashboard deve possuir quatro métricas:

1. Empresas encontradas.
2. Empresas analisadas.
3. Site não encontrado — somente `website_status === "not_found"`.
4. Com contato direto — pelo menos um valor em `phone`, `mobile`, `whatsapp` ou `email`.

### 11.3 Links de contato

| Canal | Destino |
|---|---|
| Telefone/celular | `tel:` |
| WhatsApp | `https://wa.me/...` |
| E-mail | `mailto:` |
| Instagram/Facebook/LinkedIn | URL externa em nova aba |
| Website | URL externa em nova aba |

---

## 12. Configuração backend relacionada ao contrato

Variáveis opcionais:

```env
BRAVE_SEARCH_API_KEY=
WEBSITE_DISCOVERY_ENABLED=false
```

Regras:

1. `WEBSITE_DISCOVERY_ENABLED=false` impede chamadas à busca.
2. Ausência de chave não falha o pipeline.
3. Busca desabilitada, indisponível ou com falha produz `unknown` quando não houver outra evidência.
4. A chave nunca é exposta no frontend.
5. A busca é limitada a uma chamada por lead e aos cinco primeiros resultados.
6. A concorrência dessa etapa é limitada a três leads simultâneos.

---

## 13. Erros HTTP

A API preserva o envelope padrão do FastAPI:

```json
{
  "detail": "mensagem"
}
```

A Alpha 0.1 não introduz novo formato global de erro.

Falhas de busca externa ou verificação isolada de website não devem falhar a pesquisa inteira. Elas devem ser registradas nos logs e convertidas em estado funcional apropriado, principalmente `unknown`.

---

## 14. Testes de contrato obrigatórios

O backend deve provar:

1. endpoints existentes continuam respondendo;
2. respostas preservam campos antigos;
3. respostas incluem somente campos adicionais compatíveis;
4. `Lead` novo inclui `contacts`, `website_status` e `website_source`;
5. lead antigo é deserializado sem migration;
6. site declarado e inacessível mantém `has_website=true`;
7. `unknown` não recebe score 92;
8. `not_found` recebe score 92;
9. falha de busca externa não falha o pipeline;
10. perfil social não é classificado como website oficial.

O frontend deve provar renderização para:

1. `confirmed` acessível;
2. `confirmed` inacessível;
3. `not_found`;
4. `unknown`;
5. todos os canais de contato;
6. ausência total de contatos;
7. registro antigo sem os novos campos.

A fixture do frontend deve ser uma resposta real anonimizada do backend após a implementação.

---

## 15. Ordem de integração

1. Backend adiciona modelos e campos.
2. Backend implementa e testa detecção e contatos.
3. Backend publica sem remover contrato anterior.
4. Resposta real é inspecionada.
5. Este contrato é conferido contra a resposta publicada.
6. Frontend atualiza os tipos e fallbacks.
7. Frontend integra dashboard e animação.
8. Teste integrado é executado.
9. Alpha 0.1 é liberada.

O frontend não deve definir o contrato antes da conclusão do backend. Pode trabalhar com fixtures baseadas neste documento, mas a integração final exige resposta real.

---

## 16. Controle de mudanças

Durante a Alpha 0.1, qualquer alteração neste contrato exige:

1. justificativa arquitetural;
2. atualização deste arquivo;
3. atualização dos modelos Python e TypeScript;
4. atualização dos testes de contrato;
5. revisão antes da integração entre branches.

Não são permitidas alterações informais por prompt isolado.

---

## 17. Critério de aceite

O contrato será considerado implementado quando:

- os endpoints permanecerem inalterados;
- os campos antigos continuarem disponíveis;
- os três estados de website forem respeitados;
- contatos forem entregues na estrutura definida;
- registros antigos forem aceitos;
- o frontend não contar `unknown` como ausência confirmada;
- testes de backend, type-check, lint e build do frontend passarem;
- uma resposta real publicada estiver compatível com este documento.

---

**Fim do contrato — PS Munnin Alpha 0.1**
