"""
Schemas Pydantic para API REST.
"""
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pipeline Runs
# ---------------------------------------------------------------------------
class PipelineRunCreate(BaseModel):
    niche: str = Field(..., example="clínicas odontológicas")
    region: str = Field(..., example="Belo Horizonte, MG")
    max_results: int = Field(default=200, ge=1, le=200)


class PipelineRunResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PipelineRunDetail(BaseModel):
    id: UUID
    status: str
    niche: str
    region: str
    leads_collected: int = 0
    leads_qualified: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------
class LeadListItem(BaseModel):
    id: UUID
    company_name: str
    score: Optional[int] = None
    status: str

    class Config:
        from_attributes = True


class LeadDetail(BaseModel):
    id: UUID
    company_name: str
    status: str
    score: Optional[int] = None
    score_breakdown: Optional[Dict] = None
    priority_tier: Optional[str] = None
    analysis: Optional[Dict] = None
    outreach_messages: Optional[List[Dict]] = None


class LeadStatusUpdate(BaseModel):
    status: str


class OutreachApprove(BaseModel):
    operator_id: UUID


class OutreachResponse(BaseModel):
    status: str
    scheduled_send_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Score Weights
# ---------------------------------------------------------------------------
class ScoreWeightsUpdate(BaseModel):
    no_website: float = Field(0.25, ge=0, le=1)
    performance: float = Field(0.20, ge=0, le=1)
    seo: float = Field(0.20, ge=0, le=1)
    design: float = Field(0.20, ge=0, le=1)
    social_presence: float = Field(0.15, ge=0, le=1)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
class FunnelMetrics(BaseModel):
    coletados: int
    analisados: int
    qualificados: int
    contatados: int
    respondidos: int
    convertidos: int
    perdidos: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthCheck(BaseModel):
    status: str
    database: str
    redis: str
    llm_provider: str
