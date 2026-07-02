
import pytest
from domain_core.services.score_engine import ScoreEngine
from domain_core.entities.score import ScoreWeights, AnalysisInput
from domain_core.entities.enums import PriorityTier


class TestScoreEngine:
    def test_no_website_is_hot(self):
        """T01: Empresas sem site devem ter score alto (oportunidade maxima)"""
        engine = ScoreEngine()
        result = engine.calculate(AnalysisInput(has_website=False))
        assert result.total_score == 60
        assert result.priority_tier == PriorityTier.HOT.value

    def test_perfect_website_min_score(self):
        engine = ScoreEngine()
        result = engine.calculate(AnalysisInput(
            has_website=True,
            load_time_ms=500,
            mobile_friendly=True,
            has_ssl=True,
            seo_title_present=True,
            seo_meta_description_present=True,
            design_age_estimate="moderno",
            social_presence_score=100,
        ))
        assert result.total_score == 0
        assert result.priority_tier == PriorityTier.DISCARD.value

    def test_slow_site(self):
        engine = ScoreEngine()
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
        assert result.priority_tier == PriorityTier.WARM.value

    def test_custom_weights(self):
        weights = ScoreWeights(no_website=0.5, performance=0.1, seo=0.1, design=0.1, social_presence=0.2)
        engine = ScoreEngine(weights)
        result = engine.calculate(AnalysisInput(has_website=False))
        assert result.total_score == 50

    def test_determinism(self):
        engine = ScoreEngine()
        analysis = AnalysisInput(
            has_website=True,
            load_time_ms=3000,
            mobile_friendly=True,
            has_ssl=True,
            seo_title_present=False,
            seo_meta_description_present=True,
            design_age_estimate="datado",
            social_presence_score=50,
        )
        r1 = engine.calculate(analysis)
        r2 = engine.calculate(analysis)
        assert r1.total_score == r2.total_score
        assert r1.breakdown == r2.breakdown
