"""
Analyzer Agent — Avalia maturidade digital do site de um LeadRaw.
Responsabilidade: produzir sinais objetivos de performance, SEO, design, mobile.
"""
import re
import time
from dataclasses import dataclass
from typing import Optional
import httpx
from bs4 import BeautifulSoup


@dataclass
class LeadAnalysis:
    has_website: bool
    load_time_ms: Optional[int] = None
    mobile_friendly: Optional[bool] = None
    has_ssl: Optional[bool] = None
    seo_title_present: Optional[bool] = None
    seo_meta_description_present: Optional[bool] = None
    tech_stack_guess: Optional[str] = None
    design_age_estimate: Optional[str] = None
    screenshot_url: Optional[str] = None


class AnalyzerAgent:
    """
    Agente de análise técnica de sites.
    Usa requisições HTTP + parsing HTML (heurísticas).
    LLM é usado APENAS para classificação visual de design (screenshot) — não aqui.
    """

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout = timeout_seconds

    async def analyze(self, website: Optional[str]) -> LeadAnalysis:
        if not website:
            return LeadAnalysis(has_website=False)

        # Normaliza URL
        url = website if website.startswith("http") else f"https://{website}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                start = time.perf_counter()
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                elapsed_ms = int((time.perf_counter() - start) * 1000)

                has_ssl = url.startswith("https")
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")

                # SEO on-page
                title = soup.find("title")
                seo_title_present = bool(title and title.get_text(strip=True))
                meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
                seo_meta_description_present = bool(meta_desc and meta_desc.get("content"))

                # Mobile friendly (viewport meta)
                viewport = soup.find("meta", attrs={"name": "viewport"})
                mobile_friendly = bool(viewport)

                # Tech stack guess (heurística simples)
                tech_stack = self._guess_tech(html)

                return LeadAnalysis(
                    has_website=True,
                    load_time_ms=elapsed_ms,
                    mobile_friendly=mobile_friendly,
                    has_ssl=has_ssl,
                    seo_title_present=seo_title_present,
                    seo_meta_description_present=seo_meta_description_present,
                    tech_stack_guess=tech_stack,
                    design_age_estimate=None,  # Requer LLM multimodal (screenshot)
                    screenshot_url=None,       # Requer serviço de screenshot
                )

        except Exception:
            # Timeout, bloqueio, erro DNS — considera site inacessível
            return LeadAnalysis(
                has_website=True,  # Sabemos que existe (veio do Google Maps), mas não conseguimos analisar
                load_time_ms=None,
                mobile_friendly=None,
                has_ssl=url.startswith("https"),
                seo_title_present=None,
                seo_meta_description_present=None,
                tech_stack_guess=None,
                design_age_estimate=None,
                screenshot_url=None,
            )

    @staticmethod
    def _guess_tech(html: str) -> Optional[str]:
        techs = []
        if "wp-content" in html or "wordpress" in html.lower():
            techs.append("WordPress")
        if "react" in html.lower() or "data-reactroot" in html:
            techs.append("React")
        if "next.js" in html.lower() or "__next" in html:
            techs.append("Next.js")
        if "vue" in html.lower():
            techs.append("Vue")
        if "wix" in html.lower():
            techs.append("Wix")
        if "squarespace" in html.lower():
            techs.append("Squarespace")
        return ", ".join(techs) if techs else None
