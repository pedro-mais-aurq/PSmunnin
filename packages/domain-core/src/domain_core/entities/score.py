
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ScoreWeights:
    no_website: float = 0.60
    performance: float = 0.10
    seo: float = 0.10
    design: float = 0.10
    social_presence: float = 0.10

    def __post_init__(self):
        total = sum([self.no_website, self.performance, self.seo, self.design, self.social_presence])
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
    social_presence_score: Optional[int] = None


@dataclass(frozen=True)
class ScoreResult:
    total_score: int
    breakdown: Dict[str, dict]
    priority_tier: str
