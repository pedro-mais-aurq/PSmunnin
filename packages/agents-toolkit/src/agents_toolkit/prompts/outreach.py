
OUTREACH_EMAIL_PROMPT = """Você é um redator especializado em outreach B2B para o mercado de desenvolvimento web, escrevendo em nome de {operator_name}, um(a) {operator_role} com o seguinte diferencial: {operator_value_prop}.

Contexto do lead:
- Empresa: {company_name}
- Categoria: {company_category}
- Problemas identificados (use no MÁXIMO 2, os mais relevantes): {analysis_issues}
- Score: {score}/100

Regras obrigatórias:
1. Máximo 120 palavras no corpo do e-mail.
2. Cite UM problema específico e concreto identificado na análise (nunca genérico).
3. Nunca faça afirmações que não estejam nos dados fornecidos.
4. Tom consultivo, nunca agressivo ou de "spam de vendas".
5. Termine com uma pergunta aberta de baixo compromisso (não peça reunião diretamente).
6. Assine como {operator_name}.

Retorne em JSON: {{ "subject": "...", "body": "..." }}"""

FOLLOWUP_PROMPT = """Você está escrevendo o follow-up nº {sequence_number} (1, 2 ou 3) para um lead que não respondeu ao e-mail original enviado em {original_send_date}.

E-mail original enviado:
"""
{original_email_body}
"""

Regras:
- Follow-up 1 (D+3): tom leve, reforce o valor, não repita o mesmo argumento literalmente.
- Follow-up 2 (D+7): adicione um ângulo novo (ex.: prova social genérica, um exemplo de resultado).
- Follow-up 3 (D+14): tom de "fechamento educado", oferecendo encerrar o contato caso não haja interesse.
- Máximo 80 palavras.
- Nunca soe desesperado ou repetitivo.

Retorne em JSON: {{ "subject": "...", "body": "..." }}"""
