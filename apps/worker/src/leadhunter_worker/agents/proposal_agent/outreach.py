
import json
import os
from dataclasses import dataclass
from typing import List
import openai
from agents_toolkit.parsers.json_parser import JSONParser
from pydantic import BaseModel


class OutreachEmailSchema(BaseModel):
    subject: str
    body: str


@dataclass
class OutreachMessage:
    subject: str
    body: str
    personalization_points: List[str]


class OutreachAgent:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.client = openai.AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def draft_email(self, operator_name: str, operator_role: str, operator_value_prop: str,
                        company_name: str, company_category: str, analysis_issues: List[str], score: int) -> OutreachMessage:
        prompt = f"""Você é um redator especializado em outreach B2B para o mercado de desenvolvimento web, escrevendo em nome de {operator_name}, um(a) {operator_role} com o seguinte diferencial: {operator_value_prop}.

Contexto do lead:
- Empresa: {company_name}
- Categoria: {company_category}
- Problemas identificados (use no MÁXIMO 2): {', '.join(analysis_issues)}
- Score: {score}/100

Regras obrigatórias:
1. Máximo 120 palavras no corpo.
2. Cite UM problema específico e concreto.
3. Não invente informações.
4. Tom consultivo, nunca agressivo.
5. Termine com pergunta aberta de baixo compromisso.
6. Assine como {operator_name}.

Retorne em JSON: {{ "subject": "...", "body": "..." }}"""

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
        parsed = JSONParser.parse(raw, OutreachEmailSchema)
        return OutreachMessage(
            subject=parsed.subject,
            body=parsed.body,
            personalization_points=analysis_issues[:2],
        )
