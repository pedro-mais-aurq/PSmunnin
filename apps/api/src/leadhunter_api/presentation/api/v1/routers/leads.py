
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from leadhunter_api.infrastructure.database.connection import get_db
from leadhunter_api.infrastructure.database.models.lead_model import (
    LeadModel, CompanyModel, ScoreModel, AnalysisModel, OutreachMessageModel
)
from leadhunter_api.presentation.api.v1.schemas.leads import (
    LeadListItem, LeadDetail, LeadStatusUpdate, OutreachApprove, OutreachResponse
)
from domain_core.entities.enums import LeadStatus
from domain_core.services.state_machine import LeadStateMachine
from datetime import datetime, timezone

router = APIRouter()


@router.get("")
async def list_leads(
    status: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(LeadModel, CompanyModel, ScoreModel).join(CompanyModel).outerjoin(ScoreModel)

    if status:
        try:
            status_enum = LeadStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")
        query = query.where(LeadModel.status == status_enum.value)

    if min_score is not None:
        query = query.where(ScoreModel.total_score >= min_score)
    if region:
        query = query.where(CompanyModel.address.ilike(f"%{region}%"))

    result = await db.execute(query)
    items = []
    for lead, company, score in result.all():
        items.append(LeadListItem(
            id=lead.id,
            company_name=company.name,
            score=score.total_score if score else None,
            status=lead.status,
        ))
    return items


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LeadModel, CompanyModel, ScoreModel, AnalysisModel)
        .join(CompanyModel)
        .outerjoin(ScoreModel)
        .outerjoin(AnalysisModel)
        .where(LeadModel.id == lead_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead, company, score, analysis = row

    msgs_result = await db.execute(
        select(OutreachMessageModel).where(OutreachMessageModel.lead_id == lead_id)
    )
    msgs = [
        {"id": m.id, "subject": m.subject, "status": m.status, "sequence": m.sequence_number}
        for m in msgs_result.scalars().all()
    ]

    return LeadDetail(
        id=lead.id,
        company_name=company.name,
        status=lead.status,
        score=score.total_score if score else None,
        score_breakdown=score.breakdown if score else None,
        priority_tier=score.priority_tier if score else None,
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


@router.patch("/{lead_id}/status")
async def update_lead_status(lead_id: UUID, data: LeadStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LeadModel).where(LeadModel.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    try:
        new_status = LeadStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status inválido")

    try:
        LeadStateMachine.validate_transition(LeadStatus(lead.status), new_status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    lead.status = new_status.value
    await db.commit()
    return {"id": lead_id, "status": lead.status}


@router.post("/{lead_id}/outreach/approve", response_model=OutreachResponse)
async def approve_outreach(lead_id: UUID, data: OutreachApprove, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OutreachMessageModel)
        .where(OutreachMessageModel.lead_id == lead_id)
        .where(OutreachMessageModel.status == "pending_approval")
        .order_by(OutreachMessageModel.created_at.desc())
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Nenhuma mensagem pendente de aprovação")

    msg.status = "approved"
    await db.commit()
    return OutreachResponse(status="approved", scheduled_send_at=datetime.now(timezone.utc))
