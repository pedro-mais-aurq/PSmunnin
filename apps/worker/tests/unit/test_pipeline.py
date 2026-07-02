
import pytest
from leadhunter_worker.agents.collector_agent.scout import ScoutAgent
from leadhunter_worker.agents.qualifier_agent.analyzer import AnalyzerAgent
from leadhunter_worker.agents.scoring_agent.engine import ScoreEngine, AnalysisInput
from domain_core.entities.score import ScoreWeights


def test_scout_requires_api_key():
    with pytest.raises(ValueError, match="GOOGLE_PLACES_API_KEY"):
        ScoutAgent(api_key=None)


def test_analyzer_no_website():
    """T03: Analisador deve retornar has_website=False quando nao ha site"""
    import asyncio
    agent = AnalyzerAgent()
    result = asyncio.run(agent.analyze(None))
    assert result.has_website is False
    assert result.load_time_ms is None


def test_score_engine_no_website_is_hot():
    """T03: Score sem site deve ser alto (oportunidade)"""
    engine = ScoreEngine(ScoreWeights())
    result = engine.calculate(AnalysisInput(has_website=False))
    assert result.total_score == 60
    assert result.priority_tier == "hot"


def test_score_engine_with_website():
    engine = ScoreEngine(ScoreWeights())
    result = engine.calculate(AnalysisInput(
        has_website=True,
        load_time_ms=6000,
        mobile_friendly=False,
        has_ssl=False,
        seo_title_present=False,
        seo_meta_description_present=False,
        design_age_estimate="muito_datado",
        social_presence_score=0,
    ))
    assert result.total_score == 75
    assert result.priority_tier == "warm"
