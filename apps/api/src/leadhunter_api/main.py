
from fastapi import FastAPI
from leadhunter_api.presentation.api.v1.routers import pipeline, leads, metrics, health, score
from leadhunter_api.infrastructure.database.connection import init_db

app = FastAPI(
    title="LeadHunter AI API",
    description="API do sistema multiagente de prospecção B2B",
    version="1.0.0",
)

app.include_router(pipeline.router, prefix="/v1/pipeline-runs", tags=["pipeline"])
app.include_router(leads.router, prefix="/v1/leads", tags=["leads"])
app.include_router(metrics.router, prefix="/v1/metrics", tags=["metrics"])
app.include_router(health.router, prefix="/v1/health", tags=["health"])
app.include_router(score.router, prefix="/v1/operators", tags=["operators"])


@app.on_event("startup")
async def startup():
    await init_db()
