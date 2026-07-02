
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from domain_core.entities.lead import Lead, Company


class LeadRepository(ABC):
    @abstractmethod
    async def save(self, lead: Lead) -> None: ...

    @abstractmethod
    async def get_by_id(self, lead_id: UUID) -> Optional[Lead]: ...

    @abstractmethod
    async def list_by_status(self, status: str, min_score: Optional[int] = None) -> List[Lead]: ...


class CompanyRepository(ABC):
    @abstractmethod
    async def save(self, company: Company) -> None: ...

    @abstractmethod
    async def get_by_place_id(self, place_id: str) -> Optional[Company]: ...
