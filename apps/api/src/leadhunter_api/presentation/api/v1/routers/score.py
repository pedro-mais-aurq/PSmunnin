
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from leadhunter_api.infrastructure.database.connection import get_db
from leadhunter_api.infrastructure.database.models.lead_model import OperatorModel
from leadhunter_api.presentation.api.v1.schemas.score import ScoreWeightsUpdate

router = APIRouter()


@router.put("/{operator_id}/score-weights")
async def update_score_weights(operator_id: UUID, data: ScoreWeightsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OperatorModel).where(OperatorModel.id == operator_id))
    operator = result.scalar_one_or_none()
    if not operator:
        raise HTTPException(status_code=404, detail="Operador não encontrado")

    operator.score_weights_config = data.model_dump()
    await db.commit()
    return {"operator_id": operator_id, "weights": operator.score_weights_config}
