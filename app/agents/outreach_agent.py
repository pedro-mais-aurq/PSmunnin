"""
Outreach Agent — Geração de e-mail de contato personalizado.
Usa LLM (OpenAI) com prompts estruturados conforme Seção 15.2 do MASTER_CONTEXT.
"""
import json
import os
from dataclasses import dataclass
from typing import List, Optional
import openai


@dataclass
class OutreachMessage:
    subject: str
    body: str
    personalization_points: List[str]


class OutreachAgent:
    """
    Agente de redação de e-mails B2B.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.client = openai.AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def draft_email(
        self,
        operator_name: str,
        operator_role: str,
        operator_value_prop: str,
        company_name: str,
        company_category: str,
        analysis_issues: List[str],
        score: int,
    ) -> OutreachMessage:
        """
        Gera e-mail de contato inicial personalizado.
        """
        prompt = f"""Você é um redator especializado em outreach B2B para o mercado de desenvolvimento web, escrevendo em nome de {operator_name}, um(a) {operator_role} com o seguinte diferencial: {operator_value_prop}.

Contexto do lead:
- Empresa: {company_name}
- Categoria: {company_category}
- Problemas identificados (use no MÁXIMO 2, os mais relevantes): {', '.join(analysis_issues)}
- Score: {score}/100

Regras obrigatórias:
1. Máximo 120 palavras no corpo do e-mail.
2. Cite UM problema específico e concreto identificado na análise (nunca genérico).
3. Nunca faça afirmações que não estejam nos dados fornecidos.
4. Tom consultivo, nunca agressivo ou de "spam de vendas".
5. Termine com uma pergunta aberta de baixo compromisso (não peça reunião diretamente).
6. Assine como {operator_name}.

Retorne em JSON: {{ "subject": "...", "body": "..." }}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Você é um redator de e-mails B2B. Retorne apenas JSON válido."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=600,
        )

        raw = response.choices[0].message.content or "{}"
        # Limpeza básica de markdown
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        data = json.loads(raw)
        return OutreachMessage(
            subject=data["subject"],
            body=data["body"],
            personalization_points=analysis_issues[:2],
        )
