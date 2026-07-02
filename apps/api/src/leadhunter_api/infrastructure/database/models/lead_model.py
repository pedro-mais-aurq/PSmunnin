
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from leadhunter_api.infrastructure.database.models.base import Base


class CompanyModel(Base):
    __tablename__ = "company"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    place_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    website: Mapped[str] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    leads: Mapped[list["LeadModel"]] = relationship(back_populates="company")


class LeadModel(Base):
    __tablename__ = "lead"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipeline_run.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="novo", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company: Mapped["CompanyModel"] = relationship(back_populates="leads")
    pipeline_run: Mapped["PipelineRunModel"] = relationship(back_populates="leads")


class AnalysisModel(Base):
    __tablename__ = "analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), unique=True, nullable=False)
    has_website: Mapped[bool] = mapped_column(Boolean, default=False)
    load_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    mobile_friendly: Mapped[bool] = mapped_column(Boolean, nullable=True)
    has_ssl: Mapped[bool] = mapped_column(Boolean, nullable=True)
    seo_title_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    seo_meta_description_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    tech_stack_guess: Mapped[str] = mapped_column(String(255), nullable=True)
    design_age_estimate: Mapped[str] = mapped_column(String(50), nullable=True)
    screenshot_url: Mapped[str] = mapped_column(String(500), nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ScoreModel(Base):
    __tablename__ = "score"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), unique=True, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    priority_tier: Mapped[str] = mapped_column(String(50), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class OutreachMessageModel(Base):
    __tablename__ = "outreach_message"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="email")
    subject: Mapped[str] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PipelineRunModel(Base):
    __tablename__ = "pipeline_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operator.id"), nullable=False)
    niche: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    leads: Mapped[list["LeadModel"]] = relationship(back_populates="pipeline_run")


class OperatorModel(Base):
    __tablename__ = "operator"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    score_weights_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pipeline_runs: Mapped[list["PipelineRunModel"]] = relationship(back_populates="operator")
