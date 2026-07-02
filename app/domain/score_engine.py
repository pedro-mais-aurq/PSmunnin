"""
Score Engine determinístico — lógica pura de domínio, sem LLM.
Conforme ADR-004 e Seção 17 do MASTER_CONTEXT.
"""
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class DesignAge(str, Enum):
    MODERNO = "moderno"
    INTERMEDIARIO = "intermediario"
    DATADO = "datado"
    MUITO_DATADO = "muito_datado"


class PriorityTier(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISCARD = "discard"


@dataclass(frozen=True)
class ScoreWeights:
    no_website: float = 0.25
    performance: float = 0.20
    seo: float = 0.20
    design: float = 0.20
    social_presence: float = 0.15

    def __post_init__(self):
        total = self.no_website + self.performance + self.seo + self.design + self.social_presence
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Pesos devem somar 1.0, soma atual: {total}")


@dataclass(frozen=True)
class AnalysisInput:
    has_website: bool
    load_time_ms: Optional[int] = None
    mobile_friendly: Optional[bool] = None
    has_ssl: Optional[bool] = None
    seo_title_present: Optional[bool] = None
    seo_meta_description_present: Optional[bool] = None
    design_age_estimate: Optional[str] = None
    social_presence_score: Optional[int] = None  # 0-100


@dataclass(frozen=True)
class ScoreResult:
    total_score: int
    breakdown: Dict[str, dict]
    priority_tier: PriorityTier


class ScoreEngine:
    """
    Serviço de domínio puro. Determinístico, testável, auditável.
    """

    DEFAULT_WEIGHTS = ScoreWeights()
    DESIGN_AGE_MAP = {
        DesignAge.MODERNO.value: 0,
        DesignAge.INTERMEDIARIO.value: 40,
        DesignAge.DATADO.value: 75,
        DesignAge.MUITO_DATADO.value: 100,
    }

    def __init__(self, weights: Optional[ScoreWeights] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def calculate(self, analysis: AnalysisInput) -> ScoreResult:
        breakdown = {}

        # 1. Ausência de site (0-100)
        if not analysis.has_website:
            no_website_raw = 100
        else:
            no_website_raw = 0
        breakdown["no_website"] = {
            "raw": no_website_raw,
            "weight": self.weights.no_website,
            "weighted": round(no_website_raw * self.weights.no_website, 2),
        }

        # 2. Performance (0-100) — quanto mais lento, maior a pontuação (problema)
        perf_raw = 0
        if analysis.has_website and analysis.load_time_ms is not None:
            if analysis.load_time_ms > 5000:
                perf_raw = 100
            elif analysis.load_time_ms > 3000:
                perf_raw = 80
            elif analysis.load_time_ms > 1500:
                perf_raw = 50
            elif analysis.load_time_ms > 800:
                perf_raw = 20
            else:
                perf_raw = 0
        breakdown["performance"] = {
            "raw": perf_raw,
            "weight": self.weights.performance,
            "weighted": round(perf_raw * self.weights.performance, 2),
        }

        # 3. SEO on-page (0-100) — ausência de title/meta = problema
        seo_raw = 0
        if analysis.has_website:
            missing_signals = 0
            if not analysis.seo_title_present:
                missing_signals += 1
            if not analysis.seo_meta_description_present:
                missing_signals += 1
            if not analysis.has_ssl:
                missing_signals += 1
            if not analysis.mobile_friendly:
                missing_signals += 1
            # 0 sinais = 0 pontos (ótimo), 4 sinais = 100 pontos (péssimo)
            seo_raw = min(100, missing_signals * 25)
        breakdown["seo"] = {
            "raw": seo_raw,
            "weight": self.weights.seo,
            "weighted": round(seo_raw * self.weights.seo, 2),
        }

        # 4. Design/idade visual (0-100)
        design_raw = 0
        if analysis.has_website and analysis.design_age_estimate:
            design_raw = self.DESIGN_AGE_MAP.get(analysis.design_age_estimate, 50)
        breakdown["design"] = {
            "raw": design_raw,
            "weight": self.weights.design,
            "weighted": round(design_raw * self.weights.design, 2),
        }

        # 5. Presença social (0-100) — ausência de presença = oportunidade
        social_raw = 0
        if analysis.social_presence_score is not None:
            # Invertemos: 0 presença = 100 pontos (alta oportunidade)
            social_raw = 100 - analysis.social_presence_score
        breakdown["social_presence"] = {
            "raw": social_raw,
            "weight": self.weights.social_presence,
            "weighted": round(social_raw * self.weights.social_presence, 2),
        }

        total = sum(v["weighted"] for v in breakdown.values())
        total_int = int(round(total))
        total_int = max(0, min(100, total_int))

        tier = self._tier(total_int)

        return ScoreResult(total_score=total_int, breakdown=breakdown, priority_tier=tier)

    @staticmethod
    def _tier(score: int) -> PriorityTier:
        if score >= 85:
            return PriorityTier.HOT
        if score >= 70:
            return PriorityTier.WARM
        if score >= 50:
            return PriorityTier.COLD
        return PriorityTier.DISCARD
