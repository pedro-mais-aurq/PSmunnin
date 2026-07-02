
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field


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
