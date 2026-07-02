
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from leadhunter_api.infrastructure.database.connection import get_db
from leadhunter_api.infrastructure.database.models.lead_model import LeadModel
from leadhunter_api.presentation.api.v1.schemas.metrics import FunnelMetrics

router = APIRouter()


@router.get("/funnel", response_model=FunnelMetrics)
async def get_funnel_metrics(db: AsyncSession = Depends(get_db)):
    async def count_status(s):
        r = await db.execute(select(func.count(LeadModel.id)).where(LeadModel.status == s))
        return r.scalar()

    return FunnelMetrics(
        coletados=await count_status("novo"),
        analisados=await count_status("analisado"),
        qualificados=await count_status("qualificado"),
        contatados=await count_status("contatado"),
        respondidos=await count_status("respondido"),
        convertidos=await count_status("convertido"),
        perdidos=await count_status("perdido"),
    )
