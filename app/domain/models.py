"""
Entidades e agregados do domínio LeadHunter AI.
Mapeamento SQLAlchemy 2.0 + Pydantic hybrid.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, Enum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(PyEnum):
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


class PriorityTier(PyEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISCARD = "discard"


class PipelineRunStatus(PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OutreachStatus(PyEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "company"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    place_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    rating: Mapped[Optional[float]] = mapped_column(Float)
    review_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    leads: Mapped[List["Lead"]] = relationship(back_populates="company")


# ---------------------------------------------------------------------------
# Lead (Aggregate Root)
# ---------------------------------------------------------------------------
class Lead(Base):
    __tablename__ = "lead"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    pipeline_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("pipeline_run.id"))
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.NOVO, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company: Mapped["Company"] = relationship(back_populates="leads")
    pipeline_run: Mapped[Optional["PipelineRun"]] = relationship(back_populates="leads")
    analysis: Mapped[Optional["Analysis"]] = relationship(back_populates="lead", uselist=False)
    score: Mapped[Optional["Score"]] = relationship(back_populates="lead", uselist=False)
    outreach_messages: Mapped[List["OutreachMessage"]] = relationship(back_populates="lead")
    crm_events: Mapped[List["CrmEvent"]] = relationship(back_populates="lead")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
class Analysis(Base):
    __tablename__ = "analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), unique=True, nullable=False)
    has_website: Mapped[bool] = mapped_column(Boolean, default=False)
    load_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    mobile_friendly: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_ssl: Mapped[Optional[bool]] = mapped_column(Boolean)
    seo_title_present: Mapped[Optional[bool]] = mapped_column(Boolean)
    seo_meta_description_present: Mapped[Optional[bool]] = mapped_column(Boolean)
    tech_stack_guess: Mapped[Optional[str]] = mapped_column(String(255))
    design_age_estimate: Mapped[Optional[str]] = mapped_column(String(50))
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(500))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead: Mapped["Lead"] = relationship(back_populates="analysis")


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------
class Score(Base):
    __tablename__ = "score"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), unique=True, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    priority_tier: Mapped[PriorityTier] = mapped_column(Enum(PriorityTier), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead: Mapped["Lead"] = relationship(back_populates="score")


# ---------------------------------------------------------------------------
# OutreachMessage
# ---------------------------------------------------------------------------
class OutreachMessage(Base):
    __tablename__ = "outreach_message"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="email")
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    body: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[OutreachStatus] = mapped_column(Enum(OutreachStatus), default=OutreachStatus.DRAFT)
    sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead: Mapped["Lead"] = relationship(back_populates="outreach_messages")


# ---------------------------------------------------------------------------
# CrmEvent
# ---------------------------------------------------------------------------
class CrmEvent(Base):
    __tablename__ = "crm_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead: Mapped["Lead"] = relationship(back_populates="crm_events")


# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------
class Operator(Base):
    __tablename__ = "operator"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    score_weights_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pipeline_runs: Mapped[List["PipelineRun"]] = relationship(back_populates="operator")


# ---------------------------------------------------------------------------
# PipelineRun (Aggregate Root)
# ---------------------------------------------------------------------------
class PipelineRun(Base):
    __tablename__ = "pipeline_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operator.id"), nullable=False)
    niche: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PipelineRunStatus] = mapped_column(Enum(PipelineRunStatus), default=PipelineRunStatus.QUEUED)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    operator: Mapped["Operator"] = relationship(back_populates="pipeline_runs")
    leads: Mapped[List["Lead"]] = relationship(back_populates="pipeline_run")
