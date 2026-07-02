
import os
from dataclasses import dataclass
from typing import List, Optional
import httpx


@dataclass
class LeadRaw:
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    place_id: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


class ScoutAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY não configurada")
        self.base_url = "https://maps.googleapis.com/maps/api/place"

    async def search(self, niche: str, region: str, max_results: int = 60) -> List[LeadRaw]:
        query = f"{niche} em {region}"
        leads: List[LeadRaw] = []
        next_page_token: Optional[str] = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(leads) < max_results:
                params = {"query": query, "key": self.api_key, "language": "pt-BR"}
                if next_page_token:
                    params["pagetoken"] = next_page_token

                resp = await client.get(f"{self.base_url}/textsearch/json", params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break

                for place in results:
                    place_id = place.get("place_id")
                    if not place_id:
                        continue
                    detail = await self._place_details(client, place_id)
                    leads.append(LeadRaw(
                        name=place.get("name", ""),
                        address=place.get("formatted_address") or detail.get("formatted_address"),
                        phone=detail.get("formatted_phone_number"),
                        category=place.get("types", [""])[0] if place.get("types") else None,
                        place_id=place_id,
                        website=detail.get("website"),
                        rating=place.get("rating"),
                        review_count=place.get("user_ratings_total"),
                    ))
                    if len(leads) >= max_results:
                        break

                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break
        return leads

    async def _place_details(self, client: httpx.AsyncClient, place_id: str) -> dict:
        params = {
            "place_id": place_id,
            "fields": "formatted_address,formatted_phone_number,website",
            "key": self.api_key,
            "language": "pt-BR",
        }
        resp = await client.get(f"{self.base_url}/details/json", params=params)
        resp.raise_for_status()
        return resp.json().get("result", {})
