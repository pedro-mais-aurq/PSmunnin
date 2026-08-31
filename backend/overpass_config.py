"""Shared Overpass settings, usable without importing FastAPI or MongoDB."""
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

USER_AGENT = os.getenv("OSM_USER_AGENT", "PSMunninMVP/1.0").strip()

DEFAULT_OVERPASS_ENDPOINTS = (
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)


def _parse_overpass_endpoints(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return DEFAULT_OVERPASS_ENDPOINTS

    endpoints = tuple(dict.fromkeys(
        value.strip() for value in raw_value.split(",") if value.strip()
    ))
    if not endpoints:
        raise RuntimeError("OVERPASS_ENDPOINTS deve conter ao menos uma URL.")

    for endpoint in endpoints:
        try:
            parsed = urlsplit(endpoint)
            valid = (
                parsed.scheme in {"http", "https"}
                and parsed.hostname
                and parsed.port != 0
                and not parsed.username
                and not parsed.password
                and not parsed.query
                and not parsed.fragment
                and not any(character.isspace() for character in endpoint)
            )
        except ValueError:
            valid = False
        if not valid:
            # Do not echo configuration that may accidentally contain secrets.
            raise RuntimeError(
                "OVERPASS_ENDPOINTS aceita somente URLs HTTP(S) válidas, "
                "sem credenciais, query string ou fragmento."
            )
    return endpoints


OVERPASS_ENDPOINTS = _parse_overpass_endpoints(os.getenv("OVERPASS_ENDPOINTS"))
OVERPASS_TIMEOUT = httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0)
