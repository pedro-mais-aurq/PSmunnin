
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


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
    started_at: datetime | None = None
    finished_at: datetime | None = None
