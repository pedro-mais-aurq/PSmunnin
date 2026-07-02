
from domain_core.entities.enums import LeadStatus


class LeadStateMachine:
    ALLOWED = {
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
    def validate_transition(cls, current: LeadStatus, target: LeadStatus) -> bool:
        if current == target:
            return True
        if target not in cls.ALLOWED.get(current, set()):
            raise ValueError(f"Transição inválida: {current.value} -> {target.value}")
        return True
