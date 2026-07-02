"""
Tasks Celery — execução assíncrona do pipeline e follow-ups.
"""
import os
from celery import Celery
from celery.schedules import crontab

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("leadhunter", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    beat_schedule={
        "daily-pipeline-example": {
            "task": "app.workers.tasks.run_pipeline_task",
            "schedule": crontab(hour=9, minute=0),  # 9h da manhã
            "args": ("auto", "clínicas odontológicas", "Belo Horizonte, MG", 100),
        },
    },
)


@celery_app.task(bind=True, max_retries=3)
def run_pipeline_task(self, run_id: str, niche: str, region: str, max_results: int = 200):
    """
    Task principal que executa o pipeline completo.
    """
    import asyncio
    from uuid import UUID
    from app.agents.scout_agent import ScoutAgent
    from app.agents.analyzer_agent import AnalyzerAgent
    from app.agents.orchestrator import Orchestrator, PipelineContext
    from app.infrastructure.db import async_session
    from app.domain.models import PipelineRun, PipelineRunStatus, Company, Lead, Analysis, Score, LeadStatus

    async def _execute():
        async with async_session() as db:
            run_uuid = UUID(run_id) if run_id != "auto" else None
            if run_uuid:
                run = await db.get(PipelineRun, run_uuid)
                if run:
                    run.status = PipelineRunStatus.RUNNING
                    run.started_at = datetime.now(timezone.utc)
                    await db.commit()

            scout = ScoutAgent()
            analyzer = AnalyzerAgent()
            orchestrator = Orchestrator(scout=scout, analyzer=analyzer)

            # TODO: carregar operator e weights reais do banco
            ctx = PipelineContext(
                pipeline_run_id=run_uuid or UUID(int=0),
                operator_id=UUID(int=0),
                niche=niche,
                region=region,
            )

            results = await orchestrator.run(ctx, max_results=max_results)

            for r in results:
                raw = r["company"]
                analysis = r["analysis"]
                score = r["score"]

                company = Company(
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

                lead = Lead(
                    company_id=company.id,
                    pipeline_run_id=run_uuid,
                    status=r["status"],
                )
                db.add(lead)
                await db.flush()

                if analysis.has_website or analysis.load_time_ms is not None:
                    db.add(Analysis(
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

                db.add(Score(
                    lead_id=lead.id,
                    total_score=score.total_score,
                    breakdown=score.breakdown,
                    priority_tier=score.priority_tier,
                ))

            if run_uuid:
                run = await db.get(PipelineRun, run_uuid)
                if run:
                    run.status = PipelineRunStatus.COMPLETED
                    run.finished_at = datetime.now(timezone.utc)

            await db.commit()

    try:
        asyncio.run(_execute())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
