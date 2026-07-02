
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
    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout = timeout_seconds

    async def analyze(self, website: Optional[str]) -> LeadAnalysis:
        if not website:
            return LeadAnalysis(has_website=False)
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
                title = soup.find("title")
                seo_title_present = bool(title and title.get_text(strip=True))
                meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
                seo_meta_description_present = bool(meta_desc and meta_desc.get("content"))
                viewport = soup.find("meta", attrs={"name": "viewport"})
                mobile_friendly = bool(viewport)
                return LeadAnalysis(
                    has_website=True,
                    load_time_ms=elapsed_ms,
                    mobile_friendly=mobile_friendly,
                    has_ssl=has_ssl,
                    seo_title_present=seo_title_present,
                    seo_meta_description_present=seo_meta_description_present,
                    tech_stack_guess=self._guess_tech(html),
                )
        except Exception:
            return LeadAnalysis(has_website=True, has_ssl=url.startswith("https"))

    @staticmethod
    def _guess_tech(html: str) -> Optional[str]:
        techs = []
        if "wp-content" in html or "wordpress" in html.lower():
            techs.append("WordPress")
        if "wix" in html.lower():
            techs.append("Wix")
        if "squarespace" in html.lower():
            techs.append("Squarespace")
        return ", ".join(techs) if techs else None
