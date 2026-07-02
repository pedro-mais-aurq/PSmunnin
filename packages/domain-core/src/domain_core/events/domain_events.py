
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime
    trace_id: str


@dataclass(frozen=True)
class LeadCollected(DomainEvent):
    lead_id: UUID
    company_name: str


@dataclass(frozen=True)
class LeadAnalyzed(DomainEvent):
    lead_id: UUID
    has_website: bool


@dataclass(frozen=True)
class LeadScored(DomainEvent):
    lead_id: UUID
    score: int
    tier: str


@dataclass(frozen=True)
class LeadContacted(DomainEvent):
    lead_id: UUID
    message_id: UUID
    channel: str


@dataclass(frozen=True)
class LeadConverted(DomainEvent):
    lead_id: UUID
    value: Optional[float] = None


@dataclass(frozen=True)
class LeadLost(DomainEvent):
    lead_id: UUID
    reason: Optional[str] = None
