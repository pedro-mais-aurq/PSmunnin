"""
Aplicação FastAPI principal.
"""
from fastapi import FastAPI
from app.api.routes import router
from app.infrastructure.db import init_db

app = FastAPI(
    title="LeadHunter AI API",
    description="API do sistema multiagente de prospecção B2B",
    version="1.0.0",
)

app.include_router(router, prefix="/v1")


@app.on_event("startup")
async def startup():
    await init_db()
