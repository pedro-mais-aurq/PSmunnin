
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from leadhunter_api.infrastructure.database.connection import get_db
from leadhunter_api.infrastructure.database.models.lead_model import (
    PipelineRunModel, OperatorModel, LeadModel
)
from leadhunter_api.presentation.api.v1.schemas.pipeline import (
    PipelineRunCreate, PipelineRunResponse, PipelineRunDetail
)
from domain_core.entities.enums import LeadStatus

router = APIRouter()


@router.post("", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_pipeline_run(data: PipelineRunCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OperatorModel).limit(1))
    operator = result.scalar_one_or_none()
    if not operator:
        operator = OperatorModel(name="Admin", email="admin@leadhunter.ai")
        db.add(operator)
        await db.commit()
        await db.refresh(operator)

    run = PipelineRunModel(
        operator_id=operator.id,
        niche=data.niche,
        region=data.region,
        status="queued",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return PipelineRunResponse(id=run.id, status=run.status, created_at=run.created_at)


@router.get("/{run_id}", response_model=PipelineRunDetail)
async def get_pipeline_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PipelineRunModel).where(PipelineRunModel.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run não encontrado")

    leads_collected = await db.execute(
        select(func.count(LeadModel.id)).where(LeadModel.pipeline_run_id == run_id)
    )
    leads_qualified = await db.execute(
        select(func.count(LeadModel.id))
        .where(LeadModel.pipeline_run_id == run_id)
        .where(LeadModel.status == LeadStatus.QUALIFICADO.value)
    )

    return PipelineRunDetail(
        id=run.id,
        status=run.status,
        niche=run.niche,
        region=run.region,
        leads_collected=leads_collected.scalar(),
        leads_qualified=leads_qualified.scalar(),
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
