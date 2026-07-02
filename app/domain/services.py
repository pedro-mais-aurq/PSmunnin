"""
Serviços de domínio: deduplicação, transição de status, políticas.
"""
from typing import Optional, Set
from enum import Enum

from app.domain.models import LeadStatus


class LeadDeduplicationService:
    """
    Decide se uma empresa recém-coletada já existe na base.
    """

    @staticmethod
    def is_duplicate(
        place_id: Optional[str],
        phone: Optional[str],
        website: Optional[str],
        existing_place_ids: Set[str],
        existing_phones: Set[str],
        existing_websites: Set[str],
    ) -> bool:
        if place_id and place_id in existing_place_ids:
            return True
        if phone and phone in existing_phones:
            return True
        if website and website in existing_websites:
            return True
        return False


class LeadStatusTransitionService:
    """
    Máquina de estados do Lead (Seção 12.9).
    """

    ALLOWED_TRANSITIONS = {
        LeadStatus.NOVO: {LeadStatus.ANALISADO},
        LeadStatus.ANALISADO: {LeadStatus.QUALIFICADO, LeadStatus.DESCARTADO},
        LeadStatus.QUALIFICADO: {LeadStatus.CONTATADO},
        LeadStatus.CONTATADO: {LeadStatus.RESPONDIDO, LeadStatus.EM_FOLLOWUP},
        LeadStatus.EM_FOLLOWUP: {LeadStatus.RESPONDIDO, LeadStatus.PERDIDO},
        LeadStatus.RESPONDIDO: {LeadStatus.CONVERTIDO, LeadStatus.PERDIDO},
        LeadStatus.DESCARTADO: set(),
        LeadStatus.CONVERTIDO: set(),
        LeadStatus.PERDIDO: set(),
        LeadStatus.ARCHIVED: set(),
    }

    @classmethod
    def can_transition(cls, current: LeadStatus, target: LeadStatus) -> bool:
        if current == target:
            return True
        return target in cls.ALLOWED_TRANSITIONS.get(current, set())

    @classmethod
    def transition(cls, current: LeadStatus, target: LeadStatus) -> LeadStatus:
        if not cls.can_transition(current, target):
            raise ValueError(f"Transição inválida: {current.value} -> {target.value}")
        return target


class MinimumScoreToContactPolicy:
    DEFAULT_THRESHOLD = 70

    @classmethod
    def is_qualified(cls, score: int, threshold: Optional[int] = None) -> bool:
        return score >= (threshold or cls.DEFAULT_THRESHOLD)


class MaxDailyEmailPolicy:
    DEFAULT_LIMIT = 50

    @classmethod
    def can_send(cls, sent_today: int, limit: Optional[int] = None) -> bool:
        return sent_today < (limit or cls.DEFAULT_LIMIT)
