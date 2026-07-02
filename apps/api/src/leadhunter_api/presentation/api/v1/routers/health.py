
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from leadhunter_api.infrastructure.database.connection import get_db
from leadhunter_api.config.settings import settings
import redis

router = APIRouter()


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "ok"
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
    except Exception:
        redis_status = "error"

    llm_status = "ok" if settings.openai_api_key and settings.openai_api_key.startswith("sk-") else "missing"
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "llm_provider": llm_status,
    }
