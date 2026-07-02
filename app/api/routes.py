"""
Rotas FastAPI — endpoints principais.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_db
from app.domain.models import (
    PipelineRun, PipelineRunStatus, Lead, LeadStatus, Company, Score, OutreachMessage, OutreachStatus, Operator
)
from app.api.schemas import (
    PipelineRunCreate, PipelineRunResponse, PipelineRunDetail,
    LeadListItem, LeadDetail, LeadStatusUpdate, OutreachApprove, OutreachResponse,
    ScoreWeightsUpdate, FunnelMetrics, HealthCheck
)
from app.workers.tasks import run_pipeline_task

router = APIRouter()


# ---------------------------------------------------------------------------
# Pipeline Runs
# ---------------------------------------------------------------------------
@router.post("/pipeline-runs", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_pipeline_run(data: PipelineRunCreate, db: AsyncSession = Depends(get_db)):
    """Inicia uma nova execução do pipeline."""
    # MVP: assume operator único fixo
    result = await db.execute(select(Operator).limit(1))
    operator = result.scalar_one_or_none()
    if not operator:
        operator = Operator(name="Admin", email="admin@leadhunter.ai")
        db.add(operator)
        await db.commit()
        await db.refresh(operator)

    run = PipelineRun(
        operator_id=operator.id,
        niche=data.niche,
        region=data.region,
        status=PipelineRunStatus.QUEUED,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Dispara job assíncrono via Celery
    run_pipeline_task.delay(str(run.id), data.niche, data.region, data.max_results)

    return run


@router.get("/pipeline-runs/{run_id}", response_model=PipelineRunDetail)
async def get_pipeline_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run não encontrado")

    # Contagens
    leads_collected = await db.execute(
        select(func.count(Lead.id)).where(Lead.pipeline_run_id == run_id)
    )
    leads_qualified = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.pipeline_run_id == run_id)
        .where(Lead.status == LeadStatus.QUALIFICADO)
    )

    return PipelineRunDetail(
        id=run.id,
        status=run.status.value,
        niche=run.niche,
        region=run.region,
        leads_collected=leads_collected.scalar(),
        leads_qualified=leads_qualified.scalar(),
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------
@router.get("/leads", response_model=list[LeadListItem])
async def list_leads(
    status: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead, Company, Score).join(Company).outerjoin(Score)

    if status:
        query = query.where(Lead.status == status)
    if min_score is not None:
        query = query.where(Score.total_score >= min_score)
    if region:
        query = query.where(Company.address.ilike(f"%{region}%"))

    result = await db.execute(query)
    items = []
    for lead, company, score in result.all():
        items.append(LeadListItem(
            id=lead.id,
            company_name=company.name,
            score=score.total_score if score else None,
            status=lead.status.value,
        ))
    return items


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lead, Company, Score, Analysis)
        .join(Company)
        .outerjoin(Score)
        .outerjoin(Analysis)
        .where(Lead.id == lead_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead, company, score, analysis = row

    # Outreach messages
    msgs_result = await db.execute(
        select(OutreachMessage).where(OutreachMessage.lead_id == lead_id)
    )
    msgs = [
        {"id": m.id, "subject": m.subject, "status": m.status.value, "sequence": m.sequence_number}
        for m in msgs_result.scalars().all()
    ]

    return LeadDetail(
        id=lead.id,
        company_name=company.name,
        status=lead.status.value,
        score=score.total_score if score else None,
        score_breakdown=score.breakdown if score else None,
        priority_tier=score.priority_tier.value if score else None,
        analysis={
            "has_website": analysis.has_website,
            "load_time_ms": analysis.load_time_ms,
            "mobile_friendly": analysis.mobile_friendly,
            "has_ssl": analysis.has_ssl,
            "seo_title_present": analysis.seo_title_present,
            "seo_meta_description_present": analysis.seo_meta_description_present,
            "tech_stack_guess": analysis.tech_stack_guess,
            "design_age_estimate": analysis.design_age_estimate,
        } if analysis else None,
        outreach_messages=msgs,
    )


@router.patch("/leads/{lead_id}/status")
async def update_lead_status(lead_id: UUID, data: LeadStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    try:
        new_status = LeadStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status inválido")

    from app.domain.services import LeadStatusTransitionService
    lead.status = LeadStatusTransitionService.transition(lead.status, new_status)
    await db.commit()
    return {"id": lead_id, "status": lead.status.value}


@router.post("/leads/{lead_id}/outreach/approve", response_model=OutreachResponse)
async def approve_outreach(lead_id: UUID, data: OutreachApprove, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead_id)
        .where(OutreachMessage.status == OutreachStatus.PENDING_APPROVAL)
        .order_by(OutreachMessage.created_at.desc())
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Nenhuma mensagem pendente de aprovação")

    msg.status = OutreachStatus.APPROVED
    await db.commit()

    # TODO: agendar envio real via worker Celery
    return OutreachResponse(status="approved", scheduled_send_at=datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Score Weights
# ---------------------------------------------------------------------------
@router.put("/operators/{operator_id}/score-weights")
async def update_score_weights(operator_id: UUID, data: ScoreWeightsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Operator).where(Operator.id == operator_id))
    operator = result.scalar_one_or_none()
    if not operator:
        raise HTTPException(status_code=404, detail="Operador não encontrado")

    operator.score_weights_config = data.model_dump()
    await db.commit()
    return {"operator_id": operator_id, "weights": operator.score_weights_config}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
@router.get("/metrics/funnel", response_model=FunnelMetrics)
async def get_funnel_metrics(db: AsyncSession = Depends(get_db)):
    async def count_status(s):
        r = await db.execute(select(func.count(Lead.id)).where(Lead.status == s))
        return r.scalar()

    return FunnelMetrics(
        coletados=await count_status(LeadStatus.NOVO),
        analisados=await count_status(LeadStatus.ANALISADO),
        qualificados=await count_status(LeadStatus.QUALIFICADO),
        contatados=await count_status(LeadStatus.CONTATADO),
        respondidos=await count_status(LeadStatus.RESPONDIDO),
        convertidos=await count_status(LeadStatus.CONVERTIDO),
        perdidos=await count_status(LeadStatus.PERDIDO),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get("/health", response_model=HealthCheck)
async def health_check():
    # MVP: checks simples
    return HealthCheck(
        status="ok",
        database="unknown",  # TODO: ping real
        redis="unknown",
        llm_provider="unknown",
    )
