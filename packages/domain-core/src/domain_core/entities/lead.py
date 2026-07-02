
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from domain_core.entities.enums import LeadStatus, PriorityTier


@dataclass(frozen=True)
class Company:
    name: str
    place_id: Optional[str] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


@dataclass
class Lead:
    id: UUID = field(default_factory=uuid4)
    company: Company = field(default_factory=lambda: Company(name=""))
    status: LeadStatus = LeadStatus.NOVO
    score: Optional[int] = None
    priority_tier: Optional[PriorityTier] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def transition_to(self, new_status: LeadStatus) -> "Lead":
        from domain_core.services.state_machine import LeadStateMachine
        LeadStateMachine.validate_transition(self.status, new_status)
        self.status = new_status
        self.updated_at = datetime.utcnow()
        return self
