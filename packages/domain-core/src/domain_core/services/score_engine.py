
from domain_core.entities.score import ScoreWeights, AnalysisInput, ScoreResult
from domain_core.entities.enums import PriorityTier


class ScoreEngine:
    DEFAULT_WEIGHTS = ScoreWeights()
    DESIGN_AGE_MAP = {
        "moderno": 0,
        "intermediario": 40,
        "datado": 75,
        "muito_datado": 100,
    }

    def __init__(self, weights: ScoreWeights = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def calculate(self, analysis: AnalysisInput) -> ScoreResult:
        breakdown = {}

        # 1. Ausência de site (oportunidade máxima)
        no_website_raw = 100 if not analysis.has_website else 0
        breakdown["no_website"] = {
            "raw": no_website_raw,
            "weight": self.weights.no_website,
            "weighted": round(no_website_raw * self.weights.no_website, 2),
        }

        # 2. Performance
        perf_raw = 0
        if analysis.has_website and analysis.load_time_ms is not None:
            if analysis.load_time_ms > 5000: perf_raw = 100
            elif analysis.load_time_ms > 3000: perf_raw = 80
            elif analysis.load_time_ms > 1500: perf_raw = 50
            elif analysis.load_time_ms > 800: perf_raw = 20
        breakdown["performance"] = {
            "raw": perf_raw,
            "weight": self.weights.performance,
            "weighted": round(perf_raw * self.weights.performance, 2),
        }

        # 3. SEO
        seo_raw = 0
        if analysis.has_website:
            missing = 0
            if not analysis.seo_title_present: missing += 1
            if not analysis.seo_meta_description_present: missing += 1
            if not analysis.has_ssl: missing += 1
            if not analysis.mobile_friendly: missing += 1
            seo_raw = min(100, missing * 25)
        breakdown["seo"] = {
            "raw": seo_raw,
            "weight": self.weights.seo,
            "weighted": round(seo_raw * self.weights.seo, 2),
        }

        # 4. Design
        design_raw = 0
        if analysis.has_website and analysis.design_age_estimate:
            design_raw = self.DESIGN_AGE_MAP.get(analysis.design_age_estimate, 50)
        breakdown["design"] = {
            "raw": design_raw,
            "weight": self.weights.design,
            "weighted": round(design_raw * self.weights.design, 2),
        }

        # 5. Social
        social_raw = 0
        if analysis.social_presence_score is not None:
            social_raw = 100 - analysis.social_presence_score
        breakdown["social_presence"] = {
            "raw": social_raw,
            "weight": self.weights.social_presence,
            "weighted": round(social_raw * self.weights.social_presence, 2),
        }

        total = int(round(sum(v["weighted"] for v in breakdown.values())))
        total = max(0, min(100, total))
        tier = self._tier(total)

        return ScoreResult(total_score=total, breakdown=breakdown, priority_tier=tier)

    @staticmethod
    def _tier(score: int) -> str:
        if score >= 85: return PriorityTier.HOT.value
        if score >= 70: return PriorityTier.WARM.value
        if score >= 50: return PriorityTier.COLD.value
        return PriorityTier.DISCARD.value
