
from enum import Enum as PyEnum


class LeadStatus(str, PyEnum):
    NOVO = "novo"
    ANALISADO = "analisado"
    QUALIFICADO = "qualificado"
    DESCARTADO = "descartado"
    CONTATADO = "contatado"
    RESPONDIDO = "respondido"
    EM_FOLLOWUP = "em_followup"
    CONVERTIDO = "convertido"
    PERDIDO = "perdido"
    ARCHIVED = "archived"


class PriorityTier(str, PyEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISCARD = "discard"


class PipelineRunStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OutreachStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
