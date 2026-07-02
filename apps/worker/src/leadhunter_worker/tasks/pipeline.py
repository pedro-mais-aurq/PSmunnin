
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from celery import shared_task
from leadhunter_worker.celery_app import app
from leadhunter_worker.agents.collector_agent.scout import ScoutAgent
from leadhunter_worker.agents.qualifier_agent.analyzer import AnalyzerAgent
from leadhunter_worker.agents.scoring_agent.engine import ScoreEngine, AnalysisInput
from domain_core.entities.score import ScoreWeights
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from leadhunter_api.infrastructure.database.models.lead_model import (
    LeadModel, CompanyModel, AnalysisModel, ScoreModel, PipelineRunModel
)
from domain_core.entities.enums import LeadStatus

engine = create_async_engine("postgresql+asyncpg://leadhunter:leadhunter@postgres:5432/leadhunter")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@app.task(bind=True, max_retries=3)
def run_pipeline(self, run_id: str, niche: str, region: str, max_results: int = 200):
    async def _execute():
        async with async_session() as db:
            run_uuid = UUID(run_id)
            run = await db.get(PipelineRunModel, run_uuid)
            if run:
                run.status = "running"
                run.started_at = datetime.now(timezone.utc)
                await db.commit()

            scout = ScoutAgent()
            analyzer = AnalyzerAgent()
            engine = ScoreEngine(ScoreWeights())

            raw_leads = await scout.search(niche, region, max_results)

            for raw in raw_leads:
                analysis = await analyzer.analyze(raw.website)

                # P0-08: Persistir análise sempre, mesmo sem site
                score_input = AnalysisInput(
                    has_website=analysis.has_website,
                    load_time_ms=analysis.load_time_ms,
                    mobile_friendly=analysis.mobile_friendly,
                    has_ssl=analysis.has_ssl,
                    seo_title_present=analysis.seo_title_present,
                    seo_meta_description_present=analysis.seo_meta_description_present,
                    design_age_estimate=analysis.design_age_estimate,
                )
                score = engine.calculate(score_input)

                company = CompanyModel(
                    name=raw.name,
                    place_id=raw.place_id,
                    category=raw.category,
                    phone=raw.phone,
                    address=raw.address,
                    website=raw.website,
                    rating=raw.rating,
                    review_count=raw.review_count,
                )
                db.add(company)
                await db.flush()

                status = LeadStatus.QUALIFICADO.value if score.total_score >= 70 else LeadStatus.DESCARTADO.value
                lead = LeadModel(
                    company_id=company.id,
                    pipeline_run_id=run_uuid,
                    status=status,
                )
                db.add(lead)
                await db.flush()

                db.add(AnalysisModel(
                    lead_id=lead.id,
                    has_website=analysis.has_website,
                    load_time_ms=analysis.load_time_ms,
                    mobile_friendly=analysis.mobile_friendly,
                    has_ssl=analysis.has_ssl,
                    seo_title_present=analysis.seo_title_present,
                    seo_meta_description_present=analysis.seo_meta_description_present,
                    tech_stack_guess=analysis.tech_stack_guess,
                    design_age_estimate=analysis.design_age_estimate,
                ))

                db.add(ScoreModel(
                    lead_id=lead.id,
                    total_score=score.total_score,
                    breakdown=score.breakdown,
                    priority_tier=score.priority_tier,
                ))

            if run:
                run.status = "completed"
                run.finished_at = datetime.now(timezone.utc)
            await db.commit()

    try:
        count = asyncio.run(_execute())
        return {"processed": count}
    except Exception as exc:
        # P2-04: Marcar como FAILED após esgotar retries
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(run_id))
        self.retry(exc=exc, countdown=60)


async def _mark_failed(run_id: str):
    async with async_session() as db:
        run = await db.get(PipelineRunModel, UUID(run_id))
        if run:
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
