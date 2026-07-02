
import json
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class JSONParser:
    @staticmethod
    def clean_llm_output(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return raw.strip()

    @classmethod
    def parse(cls, raw: str, model: Type[T]) -> T:
        cleaned = cls.clean_llm_output(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido retornado pelo LLM: {exc}") from exc
        try:
            return model(**data)
        except ValidationError as exc:
            raise ValueError(f"Schema inválido: {exc}") from exc
