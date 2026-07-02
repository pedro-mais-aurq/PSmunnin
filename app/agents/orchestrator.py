"""
Orquestrador Multiagente — Coordena o pipeline ponta a ponta.
Scout -> Analyzer -> Score -> Outreach.
"""
import uuid
from typing import List, Optional

from app.agents.scout_agent import ScoutAgent, LeadRaw
from app.agents.analyzer_agent import AnalyzerAgent, LeadAnalysis
from app.domain.score_engine import ScoreEngine, AnalysisInput, ScoreWeights
from app.domain.services import (
    LeadDeduplicationService,
    LeadStatusTransitionService,
    MinimumScoreToContactPolicy,
)
from app.domain.models import LeadStatus, PriorityTier


class PipelineContext:
    """Contexto de execução de um pipeline run."""

    def __init__(
        self,
        pipeline_run_id: uuid.UUID,
        operator_id: uuid.UUID,
        niche: str,
        region: str,
        score_weights: Optional[ScoreWeights] = None,
    ):
        self.pipeline_run_id = pipeline_run_id
        self.operator_id = operator_id
        self.niche = niche
        self.region = region
        self.score_engine = ScoreEngine(weights=score_weights)
        self.trace_id = str(uuid.uuid4())


class Orchestrator:
    """
    Orquestrador do pipeline. Executa as etapas em sequência e persiste resultados.
    """

    def __init__(
        self,
        scout: ScoutAgent,
        analyzer: AnalyzerAgent,
        outreach=None,  # OutreachAgent (opcional no MVP até aprovação humana)
    ):
        self.scout = scout
        self.analyzer = analyzer
        self.outreach = outreach

    async def run(
        self,
        ctx: PipelineContext,
        max_results: int = 200,
        existing_place_ids: Optional[set] = None,
    ) -> List[dict]:
        """
        Executa o pipeline completo.
        Retorna lista de resultados para persistência externa (repository).
        """
        results = []
        existing_place_ids = existing_place_ids or set()

        # 1. Scout
        raw_leads = await self.scout.search(
            niche=ctx.niche,
            region=ctx.region,
            max_results=max_results,
        )

        for raw in raw_leads:
            # Deduplicação
            if LeadDeduplicationService.is_duplicate(
                place_id=raw.place_id,
                phone=raw.phone,
                website=raw.website,
                existing_place_ids=existing_place_ids,
                existing_phones=set(),
                existing_websites=set(),
            ):
                continue

            if raw.place_id:
                existing_place_ids.add(raw.place_id)

            # 2. Analyzer
            analysis = await self.analyzer.analyze(raw.website)

            # 3. Score Engine
            score_input = AnalysisInput(
                has_website=analysis.has_website,
                load_time_ms=analysis.load_time_ms,
                mobile_friendly=analysis.mobile_friendly,
                has_ssl=analysis.has_ssl,
                seo_title_present=analysis.seo_title_present,
                seo_meta_description_present=analysis.seo_meta_description_present,
                design_age_estimate=analysis.design_age_estimate,
                social_presence_score=None,  # V1+
            )
            score_result = ctx.score_engine.calculate(score_input)

            # 4. Qualificação
            is_qualified = MinimumScoreToContactPolicy.is_qualified(score_result.total_score)
            status = LeadStatus.QUALIFICADO if is_qualified else LeadStatus.DESCARTADO

            # Monta resultado para persistência
            result = {
                "trace_id": ctx.trace_id,
                "pipeline_run_id": ctx.pipeline_run_id,
                "operator_id": ctx.operator_id,
                "company": raw,
                "analysis": analysis,
                "score": score_result,
                "status": status,
            }
            results.append(result)

        return results
