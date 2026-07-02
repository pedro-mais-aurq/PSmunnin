
from pydantic import BaseModel, Field, model_validator


class ScoreWeightsUpdate(BaseModel):
    no_website: float = Field(0.60, ge=0, le=1)
    performance: float = Field(0.10, ge=0, le=1)
    seo: float = Field(0.10, ge=0, le=1)
    design: float = Field(0.10, ge=0, le=1)
    social_presence: float = Field(0.10, ge=0, le=1)

    @model_validator(mode="after")
    def validate_total(self):
        total = self.no_website + self.performance + self.seo + self.design + self.social_presence
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Pesos devem somar 1.0, soma atual: {total}")
        return self
