
from pydantic import BaseModel


class FunnelMetrics(BaseModel):
    coletados: int
    analisados: int
    qualificados: int
    contatados: int
    respondidos: int
    convertidos: int
    perdidos: int


class HealthCheck(BaseModel):
    status: str
    database: str
    redis: str
    llm_provider: str
