# PROJECT_EXECUTION_GUIDE.md

**Projeto:** PSmunnin
**Versão:** 1.0.0
**Status:** Documento Normativo
**Prioridade:** Máxima
**Objetivo:** Definir a sequência oficial de desenvolvimento do projeto e servir como referência permanente para todas as decisões futuras.

---

## Índice

1. [Finalidade](#1-finalidade)
2. [Escopo](#2-escopo)
3. [Princípios Fundamentais](#3-princípios-fundamentais)
4. [Fluxo Oficial do Projeto](#4-fluxo-oficial-do-projeto)
5. [Ordem de Prioridade](#5-ordem-de-prioridade)
6. [Regras para Tomada de Decisão](#6-regras-para-tomada-de-decisão)
7. [Critério de Conclusão de uma Etapa](#7-critério-de-conclusão-de-uma-etapa)
8. [Controle de Mudanças](#8-controle-de-mudanças)
9. [Relação com os Demais Documentos](#9-relação-com-os-demais-documentos)
10. [Regra de Consistência para Assistentes de IA](#10-regra-de-consistência-para-assistentes-de-ia)
11. [Cláusula de Estabilidade](#11-cláusula-de-estabilidade)

---

## 1. Finalidade

Este documento estabelece a **ordem oficial de evolução** do projeto **PSmunnin**.

Sua função é garantir consistência durante todo o desenvolvimento, evitando mudanças de direção, contradições e retrabalho.

Toda recomendação, planejamento ou decisão deverá respeitar a sequência estabelecida neste documento.

> **Importante:** este documento **não descreve detalhes técnicos de implementação**. Sua responsabilidade é definir **o caminho oficial do projeto**.

---

## 2. Escopo

Este documento é aplicável a:

- Planejamento do projeto
- Desenvolvimento
- Arquitetura
- Documentação
- Assistentes de IA
- Desenvolvedores
- Futuros colaboradores

Sempre que houver dúvida sobre o próximo passo do projeto, este documento deverá ser consultado **antes de qualquer outra documentação**.

---

## 3. Princípios Fundamentais

| # | Princípio | Descrição |
|---|---|---|
| **P1** | Receita antes da Plataforma | O objetivo inicial do projeto é validar a geração de oportunidades comerciais. A construção de funcionalidades deve ocorrer apenas quando contribuir diretamente para esse objetivo. Nunca desenvolver funcionalidades apenas porque parecem interessantes. |
| **P2** | Uma etapa por vez | O projeto evolui por etapas. Cada etapa possui objetivos próprios. Nenhuma etapa deve ser iniciada antes da conclusão da anterior. |
| **P3** | Documentação antes da Implementação | Toda implementação relevante deve possuir documentação correspondente. A documentação faz parte do produto. Código sem documentação é considerado incompleto. |
| **P4** | Simplicidade primeiro | Sempre iniciar pela menor solução capaz de validar uma hipótese. Complexidade só deve ser adicionada quando houver necessidade comprovada. |
| **P5** | Evolução incremental | O projeto deve crescer continuamente. Cada versão deve representar uma evolução natural da anterior. Evitar grandes reescritas. |
| **P6** | Decisões registradas | Toda decisão arquitetural importante deverá ser registrada em um ADR (Architecture Decision Record). Mudanças futuras não substituem decisões anteriores; elas devem complementá-las. |

---

## 4. Fluxo Oficial do Projeto

O PSmunnin deverá evoluir **exatamente** na seguinte ordem.

### Visão Geral das Etapas

| Etapa | Nome | Objetivo Resumido |
|---|---|---|
| 1 | Definição do MVP | Definir o problema a ser resolvido pela primeira versão |
| 2 | Documentação Base | Construir a documentação que orienta o desenvolvimento |
| 3 | Arquitetura | Projetar a arquitetura completa antes de implementar |
| 4 | Modelo de Dados | Definir toda a estrutura de dados do sistema |
| 5 | Arquitetura dos Agentes | Definir responsabilidades e limites de cada agente de IA |
| 6 | Protótipo da Interface | Definir a experiência do usuário antes da implementação |
| 7 | Implementação do Backend | Construir toda a lógica de negócio |
| 8 | Implementação do Frontend | Construir a interface da aplicação |
| 9 | Integrações | Conectar todos os serviços externos |
| 10 | Testes | Garantir a estabilidade do sistema |
| 11 | Deploy | Publicar a primeira versão operacional |
| 12 | Validação Comercial | Validar que o sistema gera oportunidades reais |
| 13 | Evolução para SaaS | Transformar a ferramenta interna em produto comercial |

---

### ETAPA 1 — Definição do MVP

**Objetivo:** Definir claramente o problema que será resolvido pela primeira versão.

**Entregáveis:**
- Escopo do MVP
- Objetivos do MVP
- Critérios de sucesso

**Critério de conclusão:** o escopo do MVP está congelado e aprovado.

---

### ETAPA 2 — Documentação Base

**Objetivo:** Construir toda a documentação necessária para orientar o desenvolvimento.

**Entregáveis:**
- `MASTER_CONTEXT.md`
- `PROJECT_CHARTER.md`
- `PRODUCT_REQUIREMENTS.md`
- `BUSINESS_RULES.md`
- `ROADMAP.md`

**Critério de conclusão:** toda documentação essencial está criada e revisada.

---

### ETAPA 3 — Arquitetura

**Objetivo:** Projetar a arquitetura completa do sistema antes da implementação.

**Entregáveis:**
- Arquitetura geral
- Componentes
- Serviços
- Diagramas
- Fluxos

**Critério de conclusão:** arquitetura aprovada e documentada.

---

### ETAPA 4 — Modelo de Dados

**Objetivo:** Definir toda a estrutura de dados do sistema.

**Entregáveis:**
- Modelo relacional
- Entidades
- Relacionamentos
- Índices
- Restrições

**Critério de conclusão:** modelo de dados validado.

---

### ETAPA 5 — Arquitetura dos Agentes

**Objetivo:** Definir responsabilidades e limites de cada agente de IA.

**Entregáveis** (para cada agente):
- Responsabilidade
- Entradas
- Saídas
- Ferramentas
- Limitações
- Critérios de sucesso

**Critério de conclusão:** pipeline completo documentado.

---

### ETAPA 6 — Protótipo da Interface

**Objetivo:** Definir a experiência do usuário antes da implementação.

**Entregáveis:**
- Fluxos
- Wireframes
- Navegação
- Jornada do usuário

**Critério de conclusão:** interface aprovada.

---

### ETAPA 7 — Implementação do Backend

**Objetivo:** Construir toda a lógica de negócio.

**Entregáveis:**
- API
- Banco
- Serviços
- Regras de negócio

**Critério de conclusão:** backend funcional.

---

### ETAPA 8 — Implementação do Frontend

**Objetivo:** Construir a interface da aplicação.

**Entregáveis:**
- Dashboard
- Busca
- Empresas
- CRM
- Configurações

**Critério de conclusão:** frontend integrado ao backend.

---

### ETAPA 9 — Integrações

**Objetivo:** Conectar todos os serviços externos.

**Entregáveis:**
- IA
- Email
- APIs
- Filas
- Automações

**Critério de conclusão:** fluxo operacional completo.

---

### ETAPA 10 — Testes

**Objetivo:** Garantir estabilidade do sistema.

**Entregáveis:**
- Testes unitários
- Testes de integração
- Testes E2E
- Testes de carga

**Critério de conclusão:** sistema aprovado para produção.

---

### ETAPA 11 — Deploy

**Objetivo:** Publicar a primeira versão operacional.

**Entregáveis:**
- Ambiente de produção
- Monitoramento
- Logs
- Backups

**Critério de conclusão:** sistema disponível para uso.

---

### ETAPA 12 — Validação Comercial

**Objetivo:** Validar que o sistema gera oportunidades reais.

**Entregáveis:**
- Leads gerados
- Contatos realizados
- Métricas comerciais

**Critério de conclusão:** hipótese de negócio validada.

---

### ETAPA 13 — Evolução para SaaS

**Pré-condição:** o MVP deve estar validado comercialmente.

**Objetivo:** Transformar a ferramenta interna em um produto comercial.

**Entregáveis:**
- Multiusuário
- Assinaturas
- Planos
- Cobrança
- Administração

**Critério de conclusão:** produto SaaS operacional.

---

## 5. Ordem de Prioridade

Sempre seguir esta prioridade:

1. Validar negócio.
2. Melhorar documentação.
3. Melhorar arquitetura.
4. Melhorar experiência do usuário.
5. Adicionar funcionalidades.
6. Escalar infraestrutura.

> Essa ordem não deve ser alterada sem revisão estratégica do projeto.

---

## 6. Regras para Tomada de Decisão

Sempre que surgir uma dúvida durante o desenvolvimento, aplicar a seguinte sequência:

1. Identificar a etapa atual.
2. Confirmar se a etapa está concluída.
3. Verificar se a dúvida pertence à etapa atual.
4. Caso pertença a uma etapa futura, registrar no backlog.
5. Somente iniciar uma nova etapa após concluir a atual.

---

## 7. Critério de Conclusão de uma Etapa

Uma etapa somente é considerada concluída quando:

- [ ] todos os objetivos foram atingidos;
- [ ] todos os entregáveis foram produzidos;
- [ ] toda documentação foi atualizada;
- [ ] não existem pendências bloqueantes;
- [ ] a próxima etapa pode iniciar sem retrabalho.

---

## 8. Controle de Mudanças

Este documento possui **caráter normativo**.

Ele não deve ser alterado para acomodar mudanças tecnológicas.

Mudanças nos itens abaixo **não justificam** alterações neste documento:

- Linguagens
- Frameworks
- Banco de dados
- Modelos de IA
- Provedores
- Infraestrutura
- APIs

> Alterações são permitidas **apenas** quando houver mudança na estratégia geral do produto.

---

## 9. Relação com os Demais Documentos

Este documento define **a ordem de execução**. Os detalhes são documentados em arquivos específicos:

| Documento | Conteúdo |
|---|---|
| `MASTER_CONTEXT.md` | Contexto geral |
| `PRODUCT_REQUIREMENTS.md` | Requisitos |
| `SYSTEM_ARCHITECTURE.md` | Arquitetura |
| `DATABASE.md` | Banco de dados |
| `AI_AGENTS.md` | Agentes |
| `API_SPEC.md` | APIs |
| ADRs | Decisões arquiteturais |

> Este documento **nunca substitui** esses arquivos.

---

## 10. Regra de Consistência para Assistentes de IA

Qualquer assistente de IA que participe do desenvolvimento deverá seguir obrigatoriamente este processo:

1. Consultar este documento.
2. Identificar a etapa atual.
3. Confirmar que a etapa anterior foi concluída.
4. Fornecer recomendações compatíveis apenas com a etapa atual.
5. Evitar antecipar decisões pertencentes às etapas futuras.
6. Nunca contradizer decisões já registradas sem uma revisão explícita do projeto.

---

## 11. Cláusula de Estabilidade

Este documento representa a estratégia oficial de evolução do **PSmunnin**.

Seu conteúdo deve permanecer estável durante todo o ciclo de desenvolvimento.

Mudanças devem ser **raras, justificadas e documentadas**.

Toda recomendação futura deverá ser compatível com este documento, garantindo continuidade, previsibilidade e consistência durante toda a vida do projeto.
