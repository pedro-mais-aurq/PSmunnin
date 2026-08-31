"""PS Munnin — Backend MVP
Prospecção automatizada de clientes para desenvolvedores web.

Fluxo:
1) usuário cria uma pesquisa (nicho + região)
2) backend resolve a região via Nominatim, busca empresas via Overpass API
3) analisa a presença digital de cada empresa (site, HTTPS, meta, performance)
4) calcula um score de prioridade (0-100) e grava leads
5) frontend consome os leads e gera mensagem de contato via template
"""
from __future__ import annotations

import asyncio
import difflib
import ipaddress
import json
import logging
import os
import re
import socket
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
import overpass_config
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from overpass_config import (
    OVERPASS_ENDPOINTS,
    OVERPASS_TIMEOUT,
    USER_AGENT,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "").strip()

if not MONGO_URL:
    raise RuntimeError(
        "A variável de ambiente MONGO_URL não está configurada."
    )

if not DB_NAME:
    raise RuntimeError(
        "A variável de ambiente DB_NAME não está configurada."
    )

client = AsyncIOMotorClient(
    MONGO_URL,
    serverSelectionTimeoutMS=10_000,
)

db = client[DB_NAME]

app = FastAPI(
    title="PS Munnin API",
    description="API do MVP de prospecção automatizada PS Munnin.",
    version="0.2.0",
)

api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("ps-munnin")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_OVERPASS_ENDPOINTS = overpass_config.DEFAULT_OVERPASS_ENDPOINTS
_parse_overpass_endpoints = overpass_config._parse_overpass_endpoints
OVERPASS_MAX_ROUNDS = 1
OVERPASS_UNAVAILABLE_ERROR = (
    "Os serviços de coleta de empresas estão temporariamente indisponíveis. "
    "Tente novamente mais tarde."
)
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

BRAVE_SEARCH_API_KEY = os.getenv(
    "BRAVE_SEARCH_API_KEY",
    "",
).strip()

WEBSITE_DISCOVERY_ENABLED = os.getenv(
    "WEBSITE_DISCOVERY_ENABLED",
    "false",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

WEBSITE_HTTP_TIMEOUT_SECONDS = 10
MAX_WEBSITE_REDIRECTS = 5

_ProbeOutcome = Literal[
    "reachable",
    "blocked_http",
    "not_found",
    "unknown",
    "unsafe",
]


@dataclass(frozen=True)
class _ValidatedOutboundURL:
    normalized_url: str
    original_hostname: str
    original_port: int
    validated_global_addresses: tuple[str, ...]

BACKGROUND_TASKS: dict[
    asyncio.Task[None],
    str,
] = {}

STALE_MONITOR_TASK: asyncio.Task[None] | None = None

SEARCH_HEARTBEAT_SECONDS = 30
STALE_SEARCH_SECONDS = 120

INTERRUPTED_SEARCH_ERROR = (
    "A pesquisa foi interrompida pela reinicialização "
    "do serviço. Inicie uma nova pesquisa."
)


# ---------------------------------------------------------------------------
# Nicho → OSM tag mapping
# ---------------------------------------------------------------------------
# Mapeia palavras-chave (PT-BR) a filtros OSM. Se nenhum casar, cai no fallback.
NICHO_CATALOG = {
    # -----------------------------------------------------------------------
    # Alimentação
    # -----------------------------------------------------------------------
    "restaurante": {
        "tags": [("amenity", "restaurant")],
        "aliases": [
            "restaurante",
            "restaurantes",
            "comida",
            "comidas",
            "comercio de comida",
            "comércio de comida",
            "onde comer",
        ],
    },
    "lanchonete": {
        "tags": [("amenity", "fast_food")],
        "aliases": [
            "lanchonete",
            "lanchonetes",
            "lanche",
            "lanches",
            "fast food",
            "fastfood",
            "comida rapida",
            "comida rápida",
        ],
    },
    "cafe": {
        "tags": [("amenity", "cafe")],
        "aliases": [
            "cafe",
            "cafes",
            "café",
            "cafés",
            "cafeteria",
            "cafeterias",
            "coffee",
            "coffee shop",
        ],
    },
    "bar": {
        "tags": [("amenity", "bar"), ("amenity", "pub")],
        "aliases": [
            "bar",
            "bares",
            "pub",
            "pubs",
            "boteco",
            "botecos",
            "barzinho",
            "barzinhos",
        ],
    },
    "padaria": {
        "tags": [("shop", "bakery")],
        "aliases": [
            "padaria",
            "padarias",
            "panificadora",
            "panificadoras",
            "bakery",
        ],
    },
    "pizzaria": {
        "tags": [("cuisine", "pizza")],
        "aliases": [
            "pizzaria",
            "pizzarias",
            "pizza",
            "pizzas",
        ],
    },
    "hamburgueria": {
        "tags": [("cuisine", "burger")],
        "aliases": [
            "hamburgueria",
            "hamburguerias",
            "hamburguer",
            "hambúrguer",
            "burger",
            "burguer",
            "burgers",
        ],
    },
    "sorveteria": {
        "tags": [("amenity", "ice_cream")],
        "aliases": [
            "sorveteria",
            "sorveterias",
            "sorvete",
            "sorvetes",
            "gelato",
            "ice cream",
        ],
    },

    # -----------------------------------------------------------------------
    # Saúde
    # -----------------------------------------------------------------------
    "clinica": {
        "tags": [("amenity", "clinic"), ("healthcare", "clinic")],
        "aliases": [
            "clinica",
            "clinicas",
            "clínica",
            "clínicas",
            "consultorio",
            "consultorios",
            "consultório",
            "consultórios",
            "centro medico",
            "centro médico",
            "centros medicos",
            "centros médicos",
        ],
    },
    "dentista": {
        "tags": [("amenity", "dentist"), ("healthcare", "dentist")],
        "aliases": [
            "dentista",
            "dentistas",
            "odontologia",
            "odontologico",
            "odontológico",
            "clinica odontologica",
            "clínica odontológica",
            "consultorio odontologico",
            "consultório odontológico",
        ],
    },
    "medico": {
        "tags": [("amenity", "doctors"), ("healthcare", "doctor")],
        "aliases": [
            "medico",
            "médico",
            "medicos",
            "médicos",
            "consultorio medico",
            "consultório médico",
            "clinica medica",
            "clínica médica",
            "doctor",
            "doctors",
        ],
    },
    "farmacia": {
        "tags": [("amenity", "pharmacy")],
        "aliases": [
            "farmacia",
            "farmácia",
            "farmacias",
            "farmácias",
            "drogaria",
            "drogarias",
            "pharmacy",
        ],
    },
    "veterinario": {
        "tags": [("amenity", "veterinary")],
        "aliases": [
            "veterinario",
            "veterinário",
            "veterinarios",
            "veterinários",
            "clinica veterinaria",
            "clínica veterinária",
            "hospital veterinario",
            "hospital veterinário",
            "vet",
            "pet clinic",
        ],
    },
    "fisioterapia": {
        "tags": [("healthcare", "physiotherapist")],
        "aliases": [
            "fisioterapia",
            "fisioterapeuta",
            "fisioterapeutas",
            "clinica de fisioterapia",
            "clínica de fisioterapia",
            "physiotherapy",
        ],
    },
    "psicologia": {
        "tags": [("healthcare", "psychotherapist")],
        "aliases": [
            "psicologia",
            "psicologo",
            "psicólogo",
            "psicologos",
            "psicólogos",
            "psicoterapia",
            "terapia",
            "terapeuta",
            "terapeutas",
        ],
    },

    # -----------------------------------------------------------------------
    # Beleza, estética e cuidados pessoais
    # -----------------------------------------------------------------------
    "salao": {
        "tags": [("shop", "hairdresser"), ("shop", "beauty")],
        "aliases": [
            "salao",
            "salão",
            "saloes",
            "salões",
            "salao de beleza",
            "salão de beleza",
            "cabeleireiro",
            "cabeleireiros",
            "hairdresser",
        ],
    },
    "barbearia": {
        "tags": [("shop", "hairdresser")],
        "aliases": [
            "barbearia",
            "barbearias",
            "barbeiro",
            "barbeiros",
            "barber",
            "barber shop",
        ],
    },
    "beleza": {
        "tags": [("shop", "beauty"), ("shop", "hairdresser")],
        "aliases": [
            "beleza",
            "estetica",
            "estética",
            "esteticas",
            "estéticas",
            "clinica estetica",
            "clínica estética",
            "centro estetico",
            "centro estético",
            "beauty",
        ],
    },
    "spa": {
        "tags": [("leisure", "spa")],
        "aliases": [
            "spa",
            "spas",
            "day spa",
            "massagem",
            "massagens",
            "massoterapia",
        ],
    },

    # -----------------------------------------------------------------------
    # Serviços profissionais
    # -----------------------------------------------------------------------
    "advocacia": {
        "tags": [("office", "lawyer")],
        "aliases": [
            "advogado",
            "advogados",
            "advogada",
            "advogadas",
            "advocacia",
            "advocacias",
            "escritorio de advocacia",
            "escritório de advocacia",
            "escritorios de advocacia",
            "escritórios de advocacia",
            "juridico",
            "jurídico",
            "assessoria juridica",
            "assessoria jurídica",
            "direito",
            "lawyer",
            "law office",
        ],
    },
    "contador": {
        "tags": [("office", "accountant")],
        "aliases": [
            "contador",
            "contadores",
            "contadora",
            "contadoras",
            "contabilidade",
            "contabil",
            "contábil",
            "escritorio contabil",
            "escritório contábil",
            "escritorios contabeis",
            "escritórios contábeis",
            "accountant",
            "accounting",
        ],
    },
    "imobiliaria": {
        "tags": [("office", "estate_agent")],
        "aliases": [
            "imobiliaria",
            "imobiliária",
            "imobiliarias",
            "imobiliárias",
            "corretor de imoveis",
            "corretor de imóveis",
            "corretores de imoveis",
            "corretores de imóveis",
            "estate agent",
            "real estate",
        ],
    },
    "arquitetura": {
        "tags": [("office", "architect")],
        "aliases": [
            "arquitetura",
            "arquiteto",
            "arquitetos",
            "arquiteta",
            "arquitetas",
            "escritorio de arquitetura",
            "escritório de arquitetura",
            "architect",
            "architecture",
        ],
    },
    "engenharia": {
        "tags": [("office", "engineer")],
        "aliases": [
            "engenharia",
            "engenheiro",
            "engenheiros",
            "engenheira",
            "engenheiras",
            "escritorio de engenharia",
            "escritório de engenharia",
            "engineering",
            "engineer",
        ],
    },
    "marketing": {
        "tags": [("office", "advertising_agency")],
        "aliases": [
            "marketing",
            "agencia de marketing",
            "agência de marketing",
            "marketing digital",
            "publicidade",
            "propaganda",
            "agencia de publicidade",
            "agência de publicidade",
            "advertising agency",
        ],
    },

    # -----------------------------------------------------------------------
    # Comércio local
    # -----------------------------------------------------------------------
    "mercado": {
        "tags": [("shop", "supermarket"), ("shop", "convenience")],
        "aliases": [
            "mercado",
            "mercados",
            "mercearia",
            "mercearias",
            "minimercado",
            "minimercados",
            "loja de conveniencia",
            "loja de conveniência",
            "conveniencia",
            "conveniência",
        ],
    },
    "supermercado": {
        "tags": [("shop", "supermarket")],
        "aliases": [
            "supermercado",
            "supermercados",
            "hipermercado",
            "hipermercados",
            "grocery",
            "supermarket",
        ],
    },
    "petshop": {
        "tags": [("shop", "pet")],
        "aliases": [
            "petshop",
            "pet shop",
            "petshops",
            "pet shops",
            "pet",
            "pets",
            "loja pet",
            "lojas pet",
            "loja de animais",
            "lojas de animais",
        ],
    },
    "roupa": {
        "tags": [("shop", "clothes")],
        "aliases": [
            "roupa",
            "roupas",
            "loja de roupa",
            "lojas de roupa",
            "vestuario",
            "vestuário",
            "moda",
            "boutique",
            "boutiques",
            "clothes",
            "fashion",
        ],
    },
    "sapato": {
        "tags": [("shop", "shoes")],
        "aliases": [
            "sapato",
            "sapatos",
            "calcado",
            "calçado",
            "calcados",
            "calçados",
            "sapataria",
            "sapatarias",
            "loja de sapato",
            "loja de calçados",
            "shoes",
        ],
    },
    "livraria": {
        "tags": [("shop", "books")],
        "aliases": [
            "livraria",
            "livrarias",
            "livros",
            "bookstore",
            "book shop",
        ],
    },
    "floricultura": {
        "tags": [("shop", "florist")],
        "aliases": [
            "floricultura",
            "floriculturas",
            "flores",
            "loja de flores",
            "florist",
        ],
    },
    "otica": {
        "tags": [("shop", "optician")],
        "aliases": [
            "otica",
            "ótica",
            "oticas",
            "óticas",
            "oculos",
            "óculos",
            "optica",
            "óptica",
            "optician",
        ],
    },
    "joalheria": {
        "tags": [("shop", "jewelry")],
        "aliases": [
            "joalheria",
            "joalherias",
            "joias",
            "jóias",
            "semijoias",
            "semi joias",
            "jewelry",
        ],
    },
    "papelaria": {
        "tags": [("shop", "stationery")],
        "aliases": [
            "papelaria",
            "papelarias",
            "material escolar",
            "materiais escolares",
            "stationery",
        ],
    },
    "eletronicos": {
        "tags": [("shop", "electronics")],
        "aliases": [
            "eletronicos",
            "eletrônicos",
            "eletronica",
            "eletrônica",
            "loja de eletronicos",
            "loja de eletrônicos",
            "electronics",
        ],
    },
    "informatica": {
        "tags": [("shop", "computer")],
        "aliases": [
            "informatica",
            "informática",
            "loja de informatica",
            "loja de informática",
            "computador",
            "computadores",
            "computer",
            "computer shop",
        ],
    },
    "moveis": {
        "tags": [("shop", "furniture")],
        "aliases": [
            "moveis",
            "móveis",
            "loja de moveis",
            "loja de móveis",
            "furniture",
        ],
    },
    "material de construcao": {
        "tags": [("shop", "hardware"), ("shop", "doityourself")],
        "aliases": [
            "material de construcao",
            "material de construção",
            "materiais de construcao",
            "materiais de construção",
            "loja de construcao",
            "loja de construção",
            "ferragem",
            "ferragens",
            "casa de material de construcao",
            "casa de material de construção",
            "hardware",
        ],
    },

    # -----------------------------------------------------------------------
    # Automotivo
    # -----------------------------------------------------------------------
    "oficina": {
        "tags": [("shop", "car_repair")],
        "aliases": [
            "oficina",
            "oficinas",
            "oficina mecanica",
            "oficina mecânica",
            "mecanica",
            "mecânica",
            "mecanico",
            "mecânico",
            "mecanicos",
            "mecânicos",
            "auto center",
            "car repair",
        ],
    },
    "autopecas": {
        "tags": [("shop", "car_parts")],
        "aliases": [
            "autopecas",
            "autopeças",
            "pecas automotivas",
            "peças automotivas",
            "loja de autopecas",
            "loja de autopeças",
            "car parts",
        ],
    },
    "lava rapido": {
        "tags": [("amenity", "car_wash")],
        "aliases": [
            "lava rapido",
            "lava rápido",
            "lava jato",
            "lavagem de carro",
            "car wash",
        ],
    },
    "posto de gasolina": {
        "tags": [("amenity", "fuel")],
        "aliases": [
            "posto",
            "postos",
            "posto de gasolina",
            "postos de gasolina",
            "posto de combustivel",
            "posto de combustível",
            "combustivel",
            "combustível",
            "fuel",
            "gas station",
        ],
    },
    "bicicletaria": {
        "tags": [("shop", "bicycle")],
        "aliases": [
            "bicicletaria",
            "bicicletarias",
            "loja de bicicleta",
            "lojas de bicicleta",
            "bike shop",
            "bicycle shop",
        ],
    },

    # -----------------------------------------------------------------------
    # Educação
    # -----------------------------------------------------------------------
    "escola": {
        "tags": [("amenity", "school")],
        "aliases": [
            "escola",
            "escolas",
            "colegio",
            "colégio",
            "colegios",
            "colégios",
            "ensino",
            "school",
        ],
    },
    "creche": {
        "tags": [("amenity", "kindergarten")],
        "aliases": [
            "creche",
            "creches",
            "bercario",
            "berçário",
            "educacao infantil",
            "educação infantil",
            "escola infantil",
            "kindergarten",
        ],
    },
    "autoescola": {
        "tags": [("amenity", "driving_school")],
        "aliases": [
            "autoescola",
            "auto escola",
            "autoescolas",
            "auto escolas",
            "cfc",
            "centro de formacao de condutores",
            "centro de formação de condutores",
            "driving school",
        ],
    },
    "curso": {
        "tags": [("amenity", "training")],
        "aliases": [
            "curso",
            "cursos",
            "escola de cursos",
            "curso profissionalizante",
            "cursos profissionalizantes",
            "treinamento",
            "training",
        ],
    },

    # -----------------------------------------------------------------------
    # Hospedagem e turismo
    # -----------------------------------------------------------------------
    "hotel": {
        "tags": [("tourism", "hotel")],
        "aliases": [
            "hotel",
            "hoteis",
            "hotéis",
            "hotelaria",
        ],
    },
    "pousada": {
        "tags": [("tourism", "guest_house")],
        "aliases": [
            "pousada",
            "pousadas",
            "guest house",
            "hospedagem",
        ],
    },
    "hostel": {
        "tags": [("tourism", "hostel")],
        "aliases": [
            "hostel",
            "hostels",
            "albergue",
            "albergues",
        ],
    },
    "motel": {
        "tags": [("tourism", "motel")],
        "aliases": [
            "motel",
            "moteis",
            "motéis",
        ],
    },
    "agencia de turismo": {
        "tags": [("shop", "travel_agency")],
        "aliases": [
            "agencia de turismo",
            "agência de turismo",
            "agencias de turismo",
            "agências de turismo",
            "agencia de viagem",
            "agência de viagem",
            "agencias de viagem",
            "agências de viagem",
            "travel agency",
        ],
    },

    # -----------------------------------------------------------------------
    # Serviços diversos
    # -----------------------------------------------------------------------
    "lavanderia": {
        "tags": [("shop", "laundry"), ("shop", "dry_cleaning")],
        "aliases": [
            "lavanderia",
            "lavanderias",
            "lavagem de roupa",
            "lavanderia industrial",
            "dry cleaning",
            "laundry",
        ],
    },
    "costureira": {
        "tags": [("shop", "tailor")],
        "aliases": [
            "costureira",
            "costureiras",
            "costura",
            "alfaiate",
            "alfaiates",
            "tailor",
        ],
    },
    "grafica": {
        "tags": [("shop", "copyshop")],
        "aliases": [
            "grafica",
            "gráfica",
            "graficas",
            "gráficas",
            "impressao",
            "impressão",
            "copiadora",
            "copiadoras",
            "copyshop",
        ],
    },
    "banco": {
        "tags": [("amenity", "bank")],
        "aliases": [
            "banco",
            "bancos",
            "agencia bancaria",
            "agência bancária",
            "bank",
        ],
    },
}


def _normalize_text(value: str) -> str:
    value = value.strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))

    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def _singularize_token(token: str) -> str:
    if len(token) <= 3:
        return token

    if token.endswith("oes"):
        return token[:-3] + "ao"

    if token.endswith("ais"):
        return token[:-3] + "al"

    if token.endswith("eis"):
        return token[:-3] + "el"

    if token.endswith("is"):
        return token[:-2] + "il"

    if token.endswith("s"):
        return token[:-1]

    return token


def _singularize_phrase(value: str) -> str:
    tokens = value.split()
    return " ".join(_singularize_token(token) for token in tokens)


@lru_cache(maxsize=1)
def _build_nicho_index() -> dict[str, dict]:
    index = {}

    for canonical_name, config in NICHO_CATALOG.items():
        normalized_canonical = _normalize_text(canonical_name)
        index[normalized_canonical] = {
            "canonical": canonical_name,
            "tags": config["tags"],
        }

        singular_canonical = _singularize_phrase(normalized_canonical)
        index[singular_canonical] = {
            "canonical": canonical_name,
            "tags": config["tags"],
        }

        for alias in config.get("aliases", []):
            normalized_alias = _normalize_text(alias)
            singular_alias = _singularize_phrase(normalized_alias)

            index[normalized_alias] = {
                "canonical": canonical_name,
                "tags": config["tags"],
            }

            index[singular_alias] = {
                "canonical": canonical_name,
                "tags": config["tags"],
            }

    return index


def resolve_nicho(nicho: str) -> list[tuple[str, str]]:
    index = _build_nicho_index()

    key = _normalize_text(nicho)
    singular_key = _singularize_phrase(key)

    if key in index:
        return index[key]["tags"]

    if singular_key in index:
        return index[singular_key]["tags"]

    matches = difflib.get_close_matches(
        singular_key,
        index.keys(),
        n=3,
        cutoff=0.82,
    )

    if matches:
        best_match = matches[0]
        return index[best_match]["tags"]

    supported = sorted({config["canonical"] for config in index.values()})

    raise HTTPException(
        status_code=400,
        detail={
            "message": f"Nicho não suportado: '{nicho}'.",
            "supported_niches": supported,
        },
    )
# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

SearchStatus = Literal[
    "pending",
    "running",
    "done",
    "failed",
]

LeadPriority = Literal[
    "low",
    "medium",
    "high",
]

ContactChannel = Literal[
    "email",
    "whatsapp",
    "generic",
]

WebsiteDetectionStatus = Literal[
    "confirmed",
    "not_found",
    "unknown",
]

WebsiteSource = Literal[
    "osm_website",
    "osm_contact_website",
    "osm_url",
    "email_domain",
    "web_search",
]


class SearchCreate(BaseModel):
    nicho: str = Field(min_length=2, max_length=80)
    regiao: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=25, ge=1, le=60)

    @field_validator("nicho", "regiao")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "O campo deve possuir pelo menos dois caracteres."
            )

        return normalized


class ContactInfo(BaseModel):
    phone: list[str] = Field(default_factory=list)
    mobile: list[str] = Field(default_factory=list)
    whatsapp: list[str] = Field(default_factory=list)
    email: list[str] = Field(default_factory=list)
    instagram: list[str] = Field(default_factory=list)
    facebook: list[str] = Field(default_factory=list)
    linkedin: list[str] = Field(default_factory=list)


class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    search_id: str
    name: str

    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None

    lat: float | None = None
    lon: float | None = None

    has_website: bool = False
    website_reachable: bool | None = None
    https: bool | None = None
    response_ms: int | None = None

    has_title: bool | None = None
    has_meta_description: bool | None = None
    has_viewport: bool | None = None
    has_favicon: bool | None = None

    status_code: int | None = None

    issues: list[str] = Field(default_factory=list)

    score: int = 0
    priority: LeadPriority = "low"

    contacts: ContactInfo = Field(
        default_factory=ContactInfo
    )
    website_status: WebsiteDetectionStatus = "unknown"
    website_source: WebsiteSource | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Search(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    nicho: str
    regiao: str

    status: SearchStatus = "pending"

    total_found: int = 0
    total_analyzed: int = 0

    error: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SearchDetail(BaseModel):
    search: Search
    leads: list[Lead]


class ContactMessage(BaseModel):
    subject: str
    body: str
    channel: ContactChannel


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _serialize(model: BaseModel) -> dict:
    doc = model.model_dump()
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def _deserialize_search(doc: dict) -> Search:
    doc = {
        key: value
        for key, value in doc.items()
        if key != "_id"
    }

    for key in (
        "created_at",
        "updated_at",
    ):
        if isinstance(
            doc.get(key),
            str,
        ):
            doc[key] = datetime.fromisoformat(
                doc[key]
            )

    if (
        doc.get("error") is not None
        and not isinstance(
            doc["error"],
            str,
        )
    ):
        doc["error"] = _format_error_detail(
            doc["error"]
        )

    return Search(**doc)


def _deserialize_lead(doc: dict) -> Lead:
    doc = {k: v for k, v in doc.items() if k != "_id"}

    if not isinstance(doc.get("contacts"), dict):
        doc["contacts"] = ContactInfo().model_dump()

    if "website_status" not in doc:
        doc["website_status"] = (
            "confirmed"
            if doc.get("website")
            else "unknown"
        )

    if "website_source" not in doc:
        doc["website_source"] = None

    if doc["website_status"] == "confirmed":
        doc["has_website"] = True

    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return Lead(**doc)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_error_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail

    if isinstance(detail, dict):
        message = str(
            detail.get("message")
            or "Não foi possível concluir a pesquisa."
        )

        supported_niches = detail.get("supported_niches")

        if isinstance(supported_niches, list):
            niches_text = ", ".join(
                str(item)
                for item in supported_niches
            )

            return (
                f"{message} "
                f"Nichos suportados: {niches_text}."
            )

        return json.dumps(
            detail,
            ensure_ascii=False,
            default=str,
        )

    return str(detail)


async def _update_search(
    search_id: str,
    **fields: Any,
) -> None:
    fields["updated_at"] = _utc_now_iso()

    await db.searches.update_one(
        {"id": search_id},
        {"$set": fields},
    )


def _forget_background_task(
    task: asyncio.Task[None],
) -> None:
    BACKGROUND_TASKS.pop(
        task,
        None,
    )


async def _search_heartbeat(
    search_id: str,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=SEARCH_HEARTBEAT_SECONDS,
            )

        except asyncio.TimeoutError:
            try:
                await _update_search(
                    search_id
                )

            except Exception:
                logger.exception(
                    "Não foi possível atualizar o heartbeat: "
                    "search=%s",
                    search_id,
                )


async def _fail_stale_searches() -> int:
    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(
            seconds=STALE_SEARCH_SECONDS
        )
    ).isoformat()

    result = await db.searches.update_many(
        {
            "status": {
                "$in": [
                    "pending",
                    "running",
                ]
            },
            "updated_at": {
                "$lt": cutoff,
            },
        },
        {
            "$set": {
                "status": "failed",
                "error": INTERRUPTED_SEARCH_ERROR,
                "updated_at": _utc_now_iso(),
            }
        },
    )

    return result.modified_count


async def _monitor_stale_searches() -> None:
    while True:
        try:
            await asyncio.sleep(
                SEARCH_HEARTBEAT_SECONDS
            )

            recovered_count = (
                await _fail_stale_searches()
            )

            if recovered_count:
                logger.warning(
                    "%d pesquisa(s) obsoleta(s) "
                    "foram marcadas como failed.",
                    recovered_count,
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Falha ao verificar pesquisas obsoletas."
            )


def _parse_cors_origins() -> list[str]:
    raw_value = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000",
    )

    origins: list[str] = []

    for item in raw_value.split(","):
        origin = item.strip().rstrip("/")

        if origin and origin not in origins:
            origins.append(origin)

    return origins


# ---------------------------------------------------------------------------
# Contact extraction
# ---------------------------------------------------------------------------
CONTACT_TAGS: dict[str, tuple[str, ...]] = {
    "phone": ("phone", "contact:phone"),
    "mobile": ("mobile", "contact:mobile"),
    "whatsapp": ("whatsapp", "contact:whatsapp"),
    "email": ("email", "contact:email"),
    "instagram": ("instagram", "contact:instagram"),
    "facebook": ("facebook", "contact:facebook"),
    "linkedin": ("linkedin", "contact:linkedin"),
}

SOCIAL_HOSTS: dict[str, tuple[str, ...]] = {
    "instagram": ("instagram.com",),
    "facebook": ("facebook.com", "fb.com"),
    "linkedin": ("linkedin.com",),
}

SOCIAL_CANONICAL_HOSTS = {
    "instagram": "www.instagram.com",
    "facebook": "www.facebook.com",
    "linkedin": "www.linkedin.com",
}

SOCIAL_AGGREGATOR_HOSTS = {
    "beacons.ai",
    "bio.site",
    "campsite.bio",
    "link.bio",
    "linktr.ee",
    "lnk.bio",
    "msha.ke",
    "tap.bio",
    "taplink.cc",
}

PUBLIC_EMAIL_DOMAINS = {
    "bol.com.br",
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "hotmail.com.br",
    "icloud.com",
    "live.com",
    "live.com.br",
    "mail.com",
    "msn.com",
    "outlook.com",
    "outlook.com.br",
    "proton.me",
    "protonmail.com",
    "terra.com.br",
    "uol.com.br",
    "yahoo.com",
    "yahoo.com.br",
}

GENERIC_BUSINESS_TERMS = {
    "advocacia",
    "clinica",
    "clínica",
    "comercio",
    "comércio",
    "consultorio",
    "consultório",
    "eireli",
    "empresa",
    "estudio",
    "estúdio",
    "grupo",
    "ltda",
    "me",
    "odontologia",
    "restaurante",
    "salao",
    "salão",
    "servicos",
    "serviços",
    "studio",
}

LEGAL_BUSINESS_TERMS = {
    "cia",
    "companhia",
    "eireli",
    "empresa individual",
    "inc",
    "limitada",
    "llc",
    "ltda",
    "me",
    "mei",
    "sa",
    "sociedade",
}

NORMALIZED_GENERIC_BUSINESS_TERMS = {
    _normalize_text(term)
    for term in GENERIC_BUSINESS_TERMS
}

NORMALIZED_LEGAL_BUSINESS_TERMS = {
    _normalize_text(term)
    for term in LEGAL_BUSINESS_TERMS
}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return list(value)

    return [value]


def _split_multiple_values(value: Any) -> list[str]:
    values: list[str] = []

    for item in _as_list(value):
        for part in str(item).split(";"):
            normalized = part.strip()

            if normalized:
                values.append(normalized)

    return values


def _deduplicate_values(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = value.strip()
        key = normalized.casefold()

        if not normalized or key in seen:
            continue

        seen.add(key)
        result.append(normalized)

    return result


def _parse_candidate_url(value: str):
    candidate = value.strip()

    if not candidate:
        return None

    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif not re.match(
        r"^[a-z][a-z0-9+.-]*://",
        candidate,
        re.IGNORECASE,
    ):
        candidate = "https://" + candidate

    try:
        return urlsplit(candidate)
    except ValueError:
        return None


def _social_platform(value: str) -> str | None:
    parsed = _parse_candidate_url(value)

    if not parsed or not parsed.hostname:
        return None

    host = parsed.hostname.lower().removeprefix("www.")
    host = host.removeprefix("m.")

    for platform, domains in SOCIAL_HOSTS.items():
        if any(
            host == domain
            or host.endswith("." + domain)
            for domain in domains
        ):
            return platform

    return None


def _normalize_social_url(
    platform: str,
    value: str,
) -> str:
    original = value.strip()

    if not original:
        return ""

    detected_platform = _social_platform(original)

    if detected_platform:
        if detected_platform != platform:
            return original

        parsed = _parse_candidate_url(original)

        if not parsed:
            return original

        path = parsed.path or "/"

        if platform == "instagram":
            username = path.strip("/").lstrip("@")
            path = f"/{username}/" if username else "/"

        return urlunsplit(
            (
                "https",
                SOCIAL_CANONICAL_HOSTS[platform],
                path,
                parsed.query,
                "",
            )
        )

    username = original.lstrip("@").strip("/")

    if not re.fullmatch(r"[A-Za-z0-9._-]+", username):
        return original

    if platform == "instagram":
        return f"https://www.instagram.com/{username}/"

    if platform == "facebook":
        return f"https://www.facebook.com/{username}"

    if platform == "linkedin":
        return f"https://www.linkedin.com/company/{username}/"

    return original


def _is_social_or_aggregator_url(value: str) -> bool:
    if _social_platform(value):
        return True

    parsed = _parse_candidate_url(value)

    if not parsed or not parsed.hostname:
        return False

    host = parsed.hostname.lower().removeprefix("www.")

    return any(
        host == domain
        or host.endswith("." + domain)
        for domain in SOCIAL_AGGREGATOR_HOSTS
    )


def extract_contacts(tags: dict[str, Any]) -> ContactInfo:
    extracted: dict[str, list[str]] = {
        channel: []
        for channel in CONTACT_TAGS
    }

    for channel, tag_names in CONTACT_TAGS.items():
        for tag_name in tag_names:
            extracted[channel].extend(
                _split_multiple_values(
                    tags.get(tag_name)
                )
            )

        if channel in SOCIAL_HOSTS:
            extracted[channel] = [
                _normalize_social_url(
                    channel,
                    value,
                )
                for value in extracted[channel]
            ]

    for tag_name in (
        "website",
        "contact:website",
        "url",
    ):
        for value in _split_multiple_values(
            tags.get(tag_name)
        ):
            platform = _social_platform(value)

            if platform:
                extracted[platform].append(
                    _normalize_social_url(
                        platform,
                        value,
                    )
                )

    normalized = {
        channel: _deduplicate_values(values)
        for channel, values in extracted.items()
    }

    return ContactInfo(**normalized)


def _legacy_phone(contacts: ContactInfo) -> str | None:
    for values in (
        contacts.phone,
        contacts.mobile,
        contacts.whatsapp,
    ):
        if values:
            return values[0]

    return None


# ---------------------------------------------------------------------------
# OSM data fetch
# ---------------------------------------------------------------------------
async def geocode_region(regiao: str) -> dict | None:
    """Return {area_id, bbox, display_name} for a Brazilian city query."""
    params = {
        "q": regiao,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "countrycodes": "br",
    }
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"}
    async with httpx.AsyncClient(timeout=20) as cli:
        r = await cli.get(NOMINATIM_URL, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
    if not data:
        return None
    hit = data[0]
    return {
        "display_name": hit["display_name"],
        "osm_type": hit["osm_type"],
        "osm_id": hit["osm_id"],
        "bbox": hit["boundingbox"],  # [south, north, west, east]
    }


def _build_overpass_query(filters: list[tuple[str, str]], bbox: list[str], limit: int) -> str:
    """Build Overpass QL query using the region bbox."""
    south, north, west, east = bbox[0], bbox[1], bbox[2], bbox[3]
    bbox_str = f"({south},{west},{north},{east})"
    parts = []
    for k, v in filters:
        if v == "*":
            parts.append(f'node["{k}"]["name"]{bbox_str};')
            parts.append(f'way["{k}"]["name"]{bbox_str};')
        else:
            parts.append(f'node["{k}"="{v}"]{bbox_str};')
            parts.append(f'way["{k}"="{v}"]{bbox_str};')
    body = "\n".join(parts)
    return f"[out:json][timeout:30];\n(\n{body}\n);\nout tags center {limit};"


def _safe_overpass_error_excerpt(body: str) -> str:
    """Keep only diagnostic headings, never echoed queries or arbitrary HTML."""
    diagnostics = re.findall(
        r"\b(?:line\s+\d+\s*:\s*)?(?:parse|static|runtime|syntax)\s+error\b",
        body[:4096],
        flags=re.IGNORECASE,
    )
    return " ".join("; ".join(diagnostics).split())[:240] or "[conteúdo omitido]"


async def query_overpass(query: str, *, search_id: str) -> dict[str, Any]:
    """Try the configured pool once, stopping at the first valid response."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_error: Exception | None = None
    failures: list[dict[str, str | int]] = []
    context = f"search={search_id} provider=overpass"
    async with httpx.AsyncClient(timeout=OVERPASS_TIMEOUT) as cli:
        for round_number in range(1, OVERPASS_MAX_ROUNDS + 1):
            for endpoint_index, endpoint in enumerate(OVERPASS_ENDPOINTS, start=1):
                attempt = (round_number - 1) * len(OVERPASS_ENDPOINTS) + endpoint_index
                context = (
                    f"search={search_id} provider=overpass endpoint={endpoint} "
                    f"attempt={attempt} round={round_number}"
                )
                logger.info("Overpass request: %s result=request", context)
                try:
                    response = await cli.post(endpoint, data={"data": query}, headers=headers)
                except httpx.TransportError as exc:
                    # Includes connection/read/write/pool timeouts, network and
                    # remote protocol failures. Cancellation still propagates.
                    last_error = exc
                    failures.append({"endpoint": endpoint, "error_type": type(exc).__name__})
                    logger.warning(
                        "Overpass network failure: %s result=network_failure error_type=%s",
                        context, type(exc).__name__, exc_info=True,
                    )
                    continue

                status = response.status_code
                if status == 429 or status >= 500:
                    last_error = httpx.HTTPStatusError(
                        f"Overpass temporary HTTP {status}",
                        request=response.request, response=response,
                    )
                    failures.append({"endpoint": endpoint, "error_type": "HTTPStatusError", "status": status})
                    logger.warning(
                        "Overpass temporarily unavailable: %s result=temporary_http "
                        "status=%d error_type=HTTPStatusError", context, status,
                    )
                    continue

                if not response.is_success:
                    # Rejected queries (and unexpected redirects) are not outages.
                    failures.append({"endpoint": endpoint, "error_type": "HTTPStatusError", "status": status})
                    logger.error(
                        "Overpass request rejected: %s result=rejected status=%d "
                        "error_type=HTTPStatusError response_excerpt=%s",
                        context, status, _safe_overpass_error_excerpt(response.text),
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "O serviço de coleta rejeitou a consulta de empresas. "
                            "Não foi possível concluir a pesquisa. "
                            "Informe o identificador da pesquisa ao suporte."
                        ),
                    )

                try:
                    data = response.json()
                    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
                        raise TypeError("Overpass response must contain an elements list")
                    # Overpass can send partial/empty data with an HTTP 200 runtime error.
                    if data.get("remark"):
                        raise ValueError("Overpass returned a runtime remark")
                    if any(not isinstance(element, dict) for element in data["elements"]):
                        raise TypeError("Overpass elements must be objects")
                except (ValueError, TypeError) as exc:
                    last_error = exc
                    failures.append({"endpoint": endpoint, "error_type": type(exc).__name__, "status": status})
                    logger.warning(
                        "Overpass invalid response: %s result=invalid_response "
                        "status=%d error_type=%s", context, status, type(exc).__name__,
                        exc_info=True,
                    )
                    continue

                logger.info(
                    "Overpass success: %s result=success status=%d elements=%d",
                    context, status, len(data["elements"]),
                )
                return data

    logger.error(
        "All Overpass endpoints failed: %s result=unavailable error_type=%s failures=%s",
        context, type(last_error).__name__, json.dumps(failures),
        exc_info=(type(last_error), last_error, last_error.__traceback__) if last_error else None,
    )
    raise HTTPException(status_code=503, detail=OVERPASS_UNAVAILABLE_ERROR) from last_error


async def fetch_businesses(
    nicho: str,
    regiao: str,
    limit: int,
    *,
    search_id: str,
) -> tuple[list[dict], str]:
    """Return (list of raw business dicts, resolved region display name)."""
    geocode_context = (
        f"search={search_id} provider=nominatim endpoint={NOMINATIM_URL} attempt=1"
    )
    logger.info("Collection geocode: %s result=request", geocode_context)
    try:
        region_info = await geocode_region(regiao)
    except httpx.HTTPError as exc:
        logger.warning(
            "Collection geocode: %s result=failure status=%s error_type=%s",
            geocode_context,
            exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None,
            type(exc).__name__, exc_info=True,
        )
        raise
    logger.info(
        "Collection geocode: %s result=%s",
        geocode_context, "success" if region_info else "not_found",
    )
    if not region_info:
        raise HTTPException(status_code=404, detail=f"Região não encontrada: {regiao}")

    filters = resolve_nicho(nicho)
    query = _build_overpass_query(filters, region_info["bbox"], limit)
    data = await query_overpass(query, search_id=search_id)

    elements = data["elements"]
    seen_names: set[str] = set()
    businesses: list[dict] = []
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue

        normalized_name = _normalize_text(name)

        if not normalized_name:
            continue

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        # Build address from tags
        addr_parts = [
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
            tags.get("addr:suburb"),
            tags.get("addr:city"),
        ]
        address = ", ".join([p for p in addr_parts if p]) or None
        website = (
            tags.get("website")
            or tags.get("contact:website")
            or tags.get("url")
        )
        contacts = extract_contacts(tags)
        phone = _legacy_phone(contacts)
        category = (
            tags.get("amenity")
            or tags.get("shop")
            or tags.get("office")
            or tags.get("tourism")
            or tags.get("leisure")
        )
        businesses.append(
            {
                "name": name,
                "category": category,
                "address": address,
                "phone": phone,
                "website": website,
                "contacts": contacts.model_dump(),
                "tags": tags,
                "lat": lat,
                "lon": lon,
            }
        )
        if len(businesses) >= limit:
            break
    return businesses, region_info["display_name"]


# ---------------------------------------------------------------------------
# Website analysis
# ---------------------------------------------------------------------------
def _normalize_url(url: str) -> str:
    raw_url = url.strip()

    if not raw_url:
        return ""

    if re.match(
        r"^[a-z][a-z0-9+.-]*:",
        raw_url,
        re.IGNORECASE,
    ) and not re.match(
        r"^https?://",
        raw_url,
        re.IGNORECASE,
    ):
        return ""

    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    elif not re.match(
        r"^https?://",
        raw_url,
        re.IGNORECASE,
    ):
        raw_url = "https://" + raw_url

    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return ""

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname

    if (
        scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""

    try:
        ipaddress.ip_address(
            hostname.removesuffix(".")
        )
    except ValueError:
        if "." not in hostname:
            return ""

    return urlunsplit(
        (
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.query,
            "",
        )
    )


def _url_attempts(url: str) -> list[str]:
    raw_url = url.strip()

    if not raw_url:
        return []

    if re.match(
        r"^https?://",
        raw_url,
        re.IGNORECASE,
    ):
        normalized = _normalize_url(raw_url)
        return [normalized] if normalized else []

    if re.match(
        r"^[a-z][a-z0-9+.-]*:",
        raw_url,
        re.IGNORECASE,
    ):
        return []

    raw_url = raw_url.removeprefix("//")
    attempts = [
        _normalize_url("https://" + raw_url),
        _normalize_url("http://" + raw_url),
    ]

    return _deduplicate_values(
        [attempt for attempt in attempts if attempt]
    )


def _is_global_ip_address(address: str) -> bool:
    try:
        parsed_address = ipaddress.ip_address(
            address.split("%", 1)[0]
        )
    except ValueError:
        return False

    return (
        parsed_address.is_global
        and not parsed_address.is_private
        and not parsed_address.is_loopback
        and not parsed_address.is_link_local
        and not parsed_address.is_multicast
        and not parsed_address.is_reserved
        and not parsed_address.is_unspecified
    )


async def _validate_outbound_url(
    url: str,
) -> tuple[
    Literal["allowed", "dns_error", "unsafe"],
    _ValidatedOutboundURL | None,
]:
    normalized = _normalize_url(url)

    if not normalized:
        return "unsafe", None

    try:
        parsed = urlsplit(normalized)
        port = parsed.port or (
            443
            if parsed.scheme == "https"
            else 80
        )
    except ValueError:
        return "unsafe", None

    hostname = parsed.hostname

    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return "unsafe", None

    hostname = hostname.lower().removesuffix(".")

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return "unsafe", None

    if (
        hostname == "localhost"
        or hostname.endswith(
            (
                ".localhost",
                ".local",
                ".internal",
            )
        )
    ):
        return "unsafe", None

    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        literal_address = None

    if literal_address is not None:
        if not _is_global_ip_address(str(literal_address)):
            return "unsafe", None

        destination = _ValidatedOutboundURL(
            normalized_url=normalized,
            original_hostname=hostname,
            original_port=port,
            validated_global_addresses=(
                str(literal_address),
            ),
        )
        return "allowed", destination

    try:
        records = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except OSError:
        return "dns_error", None

    addresses: list[str] = []

    for record in records:
        if not record[4]:
            continue

        address = str(record[4][0]).split("%", 1)[0]

        try:
            address = str(ipaddress.ip_address(address))
        except ValueError:
            return "unsafe", None

        if address not in addresses:
            addresses.append(address)

    if not addresses:
        return "dns_error", None

    if not all(
        _is_global_ip_address(address)
        for address in addresses
    ):
        return "unsafe", None

    destination = _ValidatedOutboundURL(
        normalized_url=normalized,
        original_hostname=hostname,
        original_port=port,
        validated_global_addresses=tuple(addresses),
    )
    return "allowed", destination


def _connection_url(
    destination: _ValidatedOutboundURL,
    address: str,
) -> str:
    parsed = urlsplit(destination.normalized_url)
    parsed_address = ipaddress.ip_address(address)
    connection_host = (
        f"[{parsed_address}]"
        if parsed_address.version == 6
        else str(parsed_address)
    )

    return urlunsplit(
        (
            parsed.scheme,
            f"{connection_host}:{destination.original_port}",
            parsed.path,
            parsed.query,
            "",
        )
    )


def _host_header(
    destination: _ValidatedOutboundURL,
) -> str:
    parsed = urlsplit(destination.normalized_url)
    hostname = destination.original_hostname

    try:
        if ipaddress.ip_address(hostname).version == 6:
            hostname = f"[{hostname}]"
    except ValueError:
        pass

    default_port = (
        443
        if parsed.scheme == "https"
        else 80
    )

    if destination.original_port != default_port:
        return f"{hostname}:{destination.original_port}"

    return hostname


async def _send_validated_request(
    destination: _ValidatedOutboundURL,
) -> httpx.Response:
    address = destination.validated_global_addresses[0]
    parsed = urlsplit(destination.normalized_url)
    extensions: dict[str, Any] = {}

    if parsed.scheme == "https":
        extensions["sni_hostname"] = (
            destination.original_hostname
        )

    request = httpx.Request(
        "GET",
        _connection_url(destination, address),
        headers={
            "Host": _host_header(destination),
            "User-Agent": USER_AGENT,
        },
        extensions=extensions,
    )

    async with httpx.AsyncClient(
        timeout=WEBSITE_HTTP_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
        limits=httpx.Limits(
            max_connections=1,
            max_keepalive_connections=0,
        ),
    ) as http_client:
        return await http_client.send(request)


def _empty_website_analysis() -> dict[str, Any]:
    return {
        "website_reachable": False,
        "https": None,
        "response_ms": None,
        "has_title": None,
        "has_meta_description": None,
        "has_viewport": None,
        "has_favicon": None,
        "status_code": None,
        "issues": [],
    }


def _analyze_website_response(
    response: httpx.Response,
    elapsed_ms: int,
) -> dict[str, Any]:
    result = _empty_website_analysis()
    final_url = str(response.url)
    html = response.text[:200_000]

    result["website_reachable"] = True
    result["status_code"] = response.status_code
    result["https"] = final_url.lower().startswith("https://")
    result["response_ms"] = elapsed_ms

    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    result["has_title"] = bool(
        title_match
        and title_match.group(1).strip()
    )

    description_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+'
        r'content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    result["has_meta_description"] = bool(
        description_match
        and description_match.group(1).strip()
    )

    result["has_viewport"] = bool(
        re.search(
            r'<meta[^>]+name=["\']viewport["\']',
            html,
            re.IGNORECASE,
        )
    )
    result["has_favicon"] = bool(
        re.search(
            r'<link[^>]+rel=["\'](?:shortcut )?icon["\']',
            html,
            re.IGNORECASE,
        )
    )

    if not result["https"]:
        result["issues"].append("Sem HTTPS")
    if not result["has_viewport"]:
        result["issues"].append(
            "Não é responsivo (sem meta viewport)"
        )
    if not result["has_title"]:
        result["issues"].append("Sem título (<title>)")
    if not result["has_meta_description"]:
        result["issues"].append(
            "Sem meta description (SEO)"
        )
    if not result["has_favicon"]:
        result["issues"].append("Sem favicon")
    if elapsed_ms > 3000:
        result["issues"].append(
            f"Site lento ({elapsed_ms}ms)"
        )

    return result


async def _probe_website(url: str) -> dict[str, Any]:
    attempts = _url_attempts(url)
    analysis = _empty_website_analysis()

    if not attempts:
        analysis["issues"] = [
            "Verificação de site inconclusiva"
        ]
        return {
            "outcome": "unsafe",
            "url": None,
            **analysis,
        }

    timed_out = False
    technical_failure = False

    try:
        for attempt in attempts:
            started = datetime.now(timezone.utc)
            logical_url = attempt
            redirects_followed = 0
            response: httpx.Response | None = None

            while True:
                validation, destination = (
                    await _validate_outbound_url(
                        logical_url
                    )
                )

                if validation == "unsafe":
                    analysis["issues"] = [
                        "Verificação de site inconclusiva"
                    ]
                    return {
                        "outcome": "unsafe",
                        "url": None,
                        **analysis,
                    }

                if (
                    validation != "allowed"
                    or destination is None
                ):
                    technical_failure = True
                    response = None
                    break

                logical_url = destination.normalized_url

                try:
                    response = await _send_validated_request(
                        destination
                    )
                except httpx.TimeoutException:
                    timed_out = True
                    technical_failure = True
                    break
                except httpx.RequestError:
                    technical_failure = True
                    break
                except Exception:
                    technical_failure = True
                    logger.exception(
                        "Falha não determinística ao verificar website."
                    )
                    break

                if (
                    response.status_code
                    in {301, 302, 303, 307, 308}
                    and response.headers.get("location")
                ):
                    if redirects_followed >= MAX_WEBSITE_REDIRECTS:
                        technical_failure = True
                        response = None
                        break

                    logical_url = urljoin(
                        logical_url,
                        response.headers["location"],
                    )
                    redirects_followed += 1
                    continue

                break

            if response is None:
                continue

            elapsed_ms = int(
                (
                    datetime.now(timezone.utc)
                    - started
                ).total_seconds()
                * 1000
            )
            final_url = logical_url
            status_code = response.status_code

            if 200 <= status_code < 400:
                return {
                    "outcome": "reachable",
                    "url": final_url,
                    **_analyze_website_response(
                        response,
                        elapsed_ms,
                    ),
                }

            if status_code in {401, 403, 429}:
                blocked = _empty_website_analysis()
                blocked.update(
                    {
                        "website_reachable": False,
                        "https": final_url.lower().startswith(
                            "https://"
                        ),
                        "response_ms": elapsed_ms,
                        "status_code": status_code,
                        "issues": [
                            "Site cadastrado, mas inacessível"
                        ],
                    }
                )
                return {
                    "outcome": "blocked_http",
                    "url": final_url,
                    **blocked,
                }

            if status_code >= 500:
                technical_failure = True

    except Exception:
        technical_failure = True
        logger.exception(
            "Falha ao inicializar verificação de website."
        )

    if technical_failure:
        analysis["issues"] = [
            "Verificação do site expirou"
            if timed_out
            else "Verificação de site inconclusiva"
        ]
        return {
            "outcome": "unknown",
            "url": _normalize_url(url) or None,
            **analysis,
        }

    return {
        "outcome": "not_found",
        "url": _normalize_url(url) or None,
        **analysis,
    }


async def analyze_website(url: str) -> dict:
    """Preserve the legacy analysis surface using the domain probe."""
    probe = await _probe_website(url)

    return {
        key: value
        for key, value in probe.items()
        if key not in {"outcome", "url"}
    }


def _corporate_email_domains(
    emails: list[str],
) -> list[str]:
    domains: list[str] = []

    for email in emails:
        normalized = email.strip().lower()

        normalized = normalized.removeprefix("mailto:")

        if normalized.count("@") != 1:
            continue

        domain = normalized.rsplit("@", 1)[1].strip(". ")

        if (
            not domain
            or "." not in domain
            or domain in PUBLIC_EMAIL_DOMAINS
        ):
            continue

        domains.append(domain)

    return _deduplicate_values(domains)


def _website_detection_result(
    status: WebsiteDetectionStatus,
    *,
    website: str | None = None,
    reachable: bool | None = None,
    source: WebsiteSource | None = None,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = _empty_website_analysis()

    if analysis:
        result.update(
            {
                key: value
                for key, value in analysis.items()
                if key in result
            }
        )

    result.update(
        {
            "website": website,
            "has_website": status == "confirmed",
            "website_reachable": reachable,
            "website_status": status,
            "website_source": source,
        }
    )

    return result


def _confirmed_from_probe(
    candidate: str,
    source: WebsiteSource,
    probe: dict[str, Any],
) -> dict[str, Any]:
    if probe.get("outcome") == "unsafe":
        return _website_detection_result(
            "unknown",
            analysis={
                "issues": [
                    "Verificação de site inconclusiva"
                ]
            },
        )

    reachable = probe["outcome"] == "reachable"
    analysis = dict(probe)

    if not reachable and not analysis.get("issues"):
        analysis["issues"] = [
            "Site cadastrado, mas inacessível"
        ]

    return _website_detection_result(
        "confirmed",
        website=(
            probe.get("url")
            or _normalize_url(candidate)
        ),
        reachable=reachable,
        source=source,
        analysis=analysis,
    )


def _search_result_url(result: Any) -> str:
    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):
        return str(result.get("url") or "").strip()

    return ""


def _is_reliable_search_result(
    result: Any,
    business_name: str,
) -> bool:
    candidate = _search_result_url(result)

    if (
        not _normalize_url(candidate)
        or _is_social_or_aggregator_url(candidate)
    ):
        return False

    normalized_name = _normalize_text(business_name)
    name_tokens = [
        token
        for token in normalized_name.split()
        if len(token) >= 3
        and token not in NORMALIZED_LEGAL_BUSINESS_TERMS
    ]

    distinctive_tokens = [
        token
        for token in name_tokens
        if token not in NORMALIZED_GENERIC_BUSINESS_TERMS
    ]

    if not distinctive_tokens:
        return False

    if isinstance(result, dict):
        normalized_title = _normalize_text(
            str(result.get("title") or "")
        )
        normalized_description = _normalize_text(
            str(result.get("description") or "")
        )
    else:
        normalized_title = ""
        normalized_description = ""

    if normalized_name and (
        normalized_name in normalized_title
        or normalized_name in normalized_description
    ):
        return True

    parsed_candidate = urlsplit(
        _normalize_url(candidate)
    )
    hostname = (
        parsed_candidate.hostname
        or ""
    ).lower().removeprefix("www.")
    hostname_label = hostname.split(".", 1)[0]
    hostname_compact = re.sub(
        r"[^a-z0-9]",
        "",
        _normalize_text(hostname_label),
    )

    evidence_tokens = set(
        (
            normalized_title
            + " "
            + normalized_description
        ).split()
    )
    matching_distinctive_terms = {
        token
        for token in distinctive_tokens
        if token in evidence_tokens
        or token in hostname_compact
    }

    if len(matching_distinctive_terms) >= 2:
        return True

    if len(distinctive_tokens) == 1:
        distinctive_token = distinctive_tokens[0]

        if (
            distinctive_token in hostname_compact
            and distinctive_token
            in set(normalized_title.split())
        ):
            return True

    commercial_name_compact = "".join(name_tokens)
    distinctive_name_compact = "".join(
        distinctive_tokens
    )

    return any(
        len(name_compact) >= 5
        and hostname_compact == name_compact
        for name_compact in {
            commercial_name_compact,
            distinctive_name_compact,
        }
    )


async def search_web_for_website(
    business_name: str,
    region: str,
) -> list[dict[str, Any]] | None:
    if not WEBSITE_DISCOVERY_ENABLED or not BRAVE_SEARCH_API_KEY:
        return None

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
    }
    params = {
        "q": f'"{business_name}" {region} site oficial',
        "count": 5,
        "country": "BR",
        "search_lang": "pt-br",
        "ui_lang": "pt-BR",
    }

    try:
        async with httpx.AsyncClient(
            timeout=WEBSITE_HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=headers,
        ) as http_client:
            response = await http_client.get(
                BRAVE_SEARCH_URL,
                params=params,
            )

        if (
            response.status_code == 429
            or response.status_code >= 500
        ):
            return None

        response.raise_for_status()
        payload = response.json()
        web_payload = payload.get("web")

        if (
            not isinstance(web_payload, dict)
            or "results" not in web_payload
            or not isinstance(
                web_payload["results"],
                list,
            )
        ):
            return None

        return [
            result
            for result in web_payload["results"][:5]
            if isinstance(result, dict)
        ]

    except (
        httpx.HTTPError,
        ValueError,
    ):
        logger.exception(
            "Serviço de busca complementar indisponível."
        )
        return None
    except Exception:
        logger.exception(
            "Falha não determinística na busca complementar."
        )
        return None


async def detect_website(
    tags: dict[str, Any],
    *,
    contacts: ContactInfo | None = None,
    business_name: str = "",
    region: str = "",
    search_semaphore: asyncio.Semaphore | None = None,
) -> dict[str, Any]:
    """Discover the official website and return the Alpha 0.1 domain fields."""
    contacts = contacts or extract_contacts(tags)

    for tag_name, source in (
        ("website", "osm_website"),
        ("contact:website", "osm_contact_website"),
        ("url", "osm_url"),
    ):
        for candidate in _split_multiple_values(
            tags.get(tag_name)
        ):
            if _is_social_or_aggregator_url(candidate):
                continue

            probe = await _probe_website(candidate)

            if probe["outcome"] == "unsafe":
                return _website_detection_result(
                    "unknown",
                    analysis={
                        "issues": [
                            "Verificação de site inconclusiva"
                        ]
                    },
                )

            return _confirmed_from_probe(
                candidate,
                source,
                probe,
            )

    technical_failure = False
    unsafe_candidate_seen = False

    for domain in _corporate_email_domains(
        contacts.email
    ):
        probe = await _probe_website(domain)

        if probe["outcome"] in {
            "reachable",
            "blocked_http",
        }:
            return _confirmed_from_probe(
                domain,
                "email_domain",
                probe,
            )

        if probe["outcome"] == "unknown":
            technical_failure = True
        elif probe["outcome"] == "unsafe":
            unsafe_candidate_seen = True

    if not WEBSITE_DISCOVERY_ENABLED or not BRAVE_SEARCH_API_KEY:
        return _website_detection_result(
            "unknown",
            analysis={
                "issues": [
                    "Verificação de site inconclusiva"
                ]
            },
        )

    if search_semaphore:
        async with search_semaphore:
            search_results = await search_web_for_website(
                business_name,
                region,
            )
    else:
        search_results = await search_web_for_website(
            business_name,
            region,
        )

    if search_results is None:
        return _website_detection_result(
            "unknown",
            analysis={
                "issues": [
                    "Verificação de site inconclusiva"
                ]
            },
        )

    for result in search_results[:5]:
        if not _is_reliable_search_result(
            result,
            business_name,
        ):
            continue

        candidate = _search_result_url(result)
        probe = await _probe_website(candidate)

        if probe["outcome"] in {
            "reachable",
            "blocked_http",
        }:
            return _confirmed_from_probe(
                candidate,
                "web_search",
                probe,
            )

        if probe["outcome"] == "unknown":
            technical_failure = True
        elif probe["outcome"] == "unsafe":
            unsafe_candidate_seen = True

    if technical_failure or unsafe_candidate_seen:
        return _website_detection_result(
            "unknown",
            analysis={
                "issues": [
                    "Verificação de site inconclusiva"
                ]
            },
        )

    return _website_detection_result(
        "not_found",
        analysis={
            "issues": [
                "Site não encontrado nas fontes consultadas"
            ]
        },
    )


def calculate_score(lead: Lead) -> tuple[int, str]:
    """Higher score = better opportunity for a web developer.

    Businesses without websites or with poor digital presence get higher scores.
    """
    if lead.website_status == "not_found":
        score = 92
    elif lead.website_status == "unknown":
        score = 50
    else:
        base = 25
        if lead.website_reachable is not True:
            base += 40  # site quebrado = ótima oportunidade
        else:
            if lead.https is False:
                base += 15
            if lead.has_viewport is False:
                base += 15
            if lead.has_title is False:
                base += 8
            if lead.has_meta_description is False:
                base += 10
            if lead.has_favicon is False:
                base += 4
            if lead.response_ms and lead.response_ms > 3000:
                base += 12
            if lead.status_code and lead.status_code >= 400:
                base += 15
        score = min(base, 95)

    if score >= 75:
        priority = "high"
    elif score >= 50:
        priority = "medium"
    else:
        priority = "low"
    return score, priority


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
async def run_pipeline(
    search: Search,
    limit: int,
) -> None:
    heartbeat_stop = asyncio.Event()

    heartbeat_task = asyncio.create_task(
        _search_heartbeat(
            search.id,
            heartbeat_stop,
        )
    )

    try:
        await _update_search(
            search.id,
            status="running",
            error=None,
        )

        businesses, _ = await fetch_businesses(
            search.nicho,
            search.regiao,
            limit,
            search_id=search.id,
        )

        await _update_search(
            search.id,
            total_found=len(businesses),
        )

        discovery_semaphore = asyncio.Semaphore(3)

        async def process_business(
            business: dict,
        ) -> Lead:
            business_tags = dict(
                business.get("tags") or {}
            )

            if (
                business.get("website")
                and not any(
                    business_tags.get(tag_name)
                    for tag_name in (
                        "website",
                        "contact:website",
                        "url",
                    )
                )
            ):
                business_tags["website"] = (
                    business["website"]
                )

            contacts_payload = business.get(
                "contacts"
            )

            if isinstance(contacts_payload, ContactInfo):
                contacts = contacts_payload
            elif isinstance(contacts_payload, dict):
                contacts = ContactInfo(
                    **contacts_payload
                )
            else:
                contacts = extract_contacts(
                    business_tags
                )

            if (
                not _legacy_phone(contacts)
                and business.get("phone")
            ):
                contacts.phone = _deduplicate_values(
                    _split_multiple_values(
                        business["phone"]
                    )
                )

            lead = Lead(
                search_id=search.id,
                name=business["name"],
                category=business.get("category"),
                address=business.get("address"),
                phone=_legacy_phone(contacts),
                lat=business.get("lat"),
                lon=business.get("lon"),
                contacts=contacts,
            )

            website_result = await detect_website(
                business_tags,
                contacts=contacts,
                business_name=lead.name,
                region=search.regiao,
                search_semaphore=discovery_semaphore,
            )

            for key, value in website_result.items():
                setattr(lead, key, value)

            score, priority = calculate_score(lead)

            lead.score = score
            lead.priority = priority

            return lead

        semaphore = asyncio.Semaphore(6)

        async def bounded_process(
            business: dict,
        ) -> Lead:
            async with semaphore:
                return await process_business(
                    business
                )

        leads = await asyncio.gather(
            *[
                bounded_process(business)
                for business in businesses
            ]
        )

        leads.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        await db.leads.delete_many(
            {"search_id": search.id}
        )

        if leads:
            await db.leads.insert_many(
                [
                    _serialize(lead)
                    for lead in leads
                ]
            )

        await _update_search(
            search.id,
            status="done",
            total_analyzed=len(leads),
            error=None,
        )

        logger.info(
            "Pipeline concluído: search=%s found=%d analyzed=%d",
            search.id,
            len(businesses),
            len(leads),
        )

    except HTTPException as exc:
        error_message = _format_error_detail(
            exc.detail
        )

        logger.warning(
            "Pipeline rejeitado: search=%s error=%s",
            search.id,
            error_message,
        )

        await _update_search(
            search.id,
            status="failed",
            error=error_message,
        )

    except Exception:
        logger.exception(
            "Falha inesperada no pipeline: search=%s",
            search.id,
        )

        await _update_search(
            search.id,
            status="failed",
            error=(
                "Não foi possível concluir a pesquisa. "
                "Tente novamente mais tarde. Se o problema persistir, "
                "informe o identificador da pesquisa ao suporte."
            ),
        )

    finally:
        heartbeat_stop.set()

        await asyncio.gather(
            heartbeat_task,
            return_exceptions=True,
        )


# ---------------------------------------------------------------------------
# Contact message template
# ---------------------------------------------------------------------------
def build_message(
    lead: Lead,
    channel: ContactChannel = "email",
) -> ContactMessage:
    name = lead.name
    issues_txt = ""
    if lead.issues:
        issues_txt = "\n".join(f"• {i}" for i in lead.issues[:5])
    else:
        issues_txt = "• Presença digital com pontos a evoluir"

    subject = f"Ideias para melhorar a presença digital da {name}"

    if channel == "whatsapp":
        body = (
            f"Olá! Vi a {name} aqui na região e gostei do trabalho de vocês.\n\n"
            f"Dei uma olhada rápida na presença digital e percebi alguns pontos "
            f"que costumam impactar diretamente em novos clientes:\n{issues_txt}\n\n"
            f"Trabalho com desenvolvimento de sites e ajudei outros negócios "
            f"parecidos a aparecerem melhor no Google e transformar visitas em "
            f"vendas. Posso preparar um diagnóstico gratuito da {name}?"
        )
    else:  # email / generic
        body = (
            f"Olá, tudo bem?\n\n"
            f"Meu nome é [Seu Nome], sou desenvolvedor(a) web e estou entrando "
            f"em contato porque conheci a {name} e acredito que posso ajudar "
            f"vocês a atrair mais clientes pela internet.\n\n"
            f"Fiz uma análise inicial da presença digital e identifiquei alguns "
            f"pontos que costumam ser decisivos para novos clientes:\n\n"
            f"{issues_txt}\n\n"
            f"Ajusto esses pontos rapidamente e monto um site moderno, rápido "
            f"e otimizado para buscas — sem complicação para vocês.\n\n"
            f"Posso enviar um diagnóstico completo e uma proposta sem "
            f"compromisso? Basta responder este contato.\n\n"
            f"Abraço,\n[Seu Nome]"
        )
    return ContactMessage(subject=subject, body=body, channel=channel)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@api_router.get("/")
async def root():
    return {
        "service": "PS Munnin API",
        "status": "ok",
    }


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")

        return {
            "status": "ok",
        }

    except Exception:
        logger.exception(
            "Falha no health check do MongoDB."
        )

        raise HTTPException(
            status_code=503,
            detail="Banco de dados indisponível.",
        )


@api_router.post(
    "/searches",
    response_model=Search,
    status_code=202,
)
async def create_search(
    payload: SearchCreate,
):
    search = Search(
        nicho=payload.nicho,
        regiao=payload.regiao,
    )

    await db.searches.insert_one(
        _serialize(search)
    )

    task = asyncio.create_task(
        run_pipeline(
            search,
            payload.limit,
        )
    )

    BACKGROUND_TASKS[task] = search.id

    task.add_done_callback(
        _forget_background_task
    )

    return search


@api_router.get(
    "/searches",
    response_model=list[Search],
)
async def list_searches():
    docs = (
        await db.searches
        .find(
            {},
            {"_id": 0},
        )
        .sort("created_at", -1)
        .to_list(200)
    )

    return [
        _deserialize_search(document)
        for document in docs
    ]


@api_router.get(
    "/searches/{search_id}",
    response_model=SearchDetail,
)
async def get_search(
    search_id: str,
):
    document = await db.searches.find_one(
        {"id": search_id},
        {"_id": 0},
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Pesquisa não encontrada.",
        )

    search = _deserialize_search(document)

    lead_documents = (
        await db.leads
        .find(
            {"search_id": search_id},
            {"_id": 0},
        )
        .sort("score", -1)
        .to_list(500)
    )

    leads = [
        _deserialize_lead(lead_document)
        for lead_document in lead_documents
    ]

    return SearchDetail(
        search=search,
        leads=leads,
    )


@api_router.delete(
    "/searches/{search_id}",
)
async def delete_search(
    search_id: str,
):
    result = await db.searches.delete_one(
        {"id": search_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Pesquisa não encontrada.",
        )

    await db.leads.delete_many(
        {"search_id": search_id}
    )

    return {
        "ok": True,
    }


@api_router.get(
    "/leads/{lead_id}",
    response_model=Lead,
)
async def get_lead(
    lead_id: str,
):
    document = await db.leads.find_one(
        {"id": lead_id},
        {"_id": 0},
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Lead não encontrado.",
        )

    return _deserialize_lead(document)


@api_router.get(
    "/leads/{lead_id}/message",
    response_model=ContactMessage,
)
async def generate_message(
    lead_id: str,
    channel: ContactChannel = "email",
):
    document = await db.leads.find_one(
        {"id": lead_id},
        {"_id": 0},
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Lead não encontrado.",
        )

    lead = _deserialize_lead(document)

    return build_message(
        lead,
        channel=channel,
    )


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
    ],
)


@app.on_event("startup")
async def startup_application() -> None:
    global STALE_MONITOR_TASK

    await db.command("ping")

    stale_count = (
        await _fail_stale_searches()
    )

    if stale_count:
        logger.warning(
            "%d pesquisa(s) obsoleta(s) "
            "foram marcadas como failed.",
            stale_count,
        )

    STALE_MONITOR_TASK = asyncio.create_task(
        _monitor_stale_searches()
    )

    await db.searches.create_index(
        "id",
        unique=True,
    )

    await db.searches.create_index(
        "created_at",
    )

    await db.leads.create_index(
        "id",
        unique=True,
    )

    await db.leads.create_index(
        "search_id",
    )

    await db.leads.create_index(
        [
            ("search_id", 1),
            ("score", -1),
        ]
    )

    logger.info(
        "Backend iniciado e índices MongoDB verificados."
    )


@app.on_event("shutdown")
async def shutdown_application() -> None:
    global STALE_MONITOR_TASK

    if STALE_MONITOR_TASK:
        STALE_MONITOR_TASK.cancel()

        await asyncio.gather(
            STALE_MONITOR_TASK,
            return_exceptions=True,
        )

        STALE_MONITOR_TASK = None

    active_items = list(
        BACKGROUND_TASKS.items()
    )

    active_search_ids = [
        search_id
        for _, search_id in active_items
    ]

    for task, _ in active_items:
        task.cancel()

    if active_items:
        await asyncio.gather(
            *[
                task
                for task, _ in active_items
            ],
            return_exceptions=True,
        )

    if active_search_ids:
        await db.searches.update_many(
            {
                "id": {
                    "$in": active_search_ids,
                },
                "status": {
                    "$in": [
                        "pending",
                        "running",
                    ]
                },
            },
            {
                "$set": {
                    "status": "failed",
                    "error": INTERRUPTED_SEARCH_ERROR,
                    "updated_at": _utc_now_iso(),
                }
            },
        )

    BACKGROUND_TASKS.clear()

    client.close()

    logger.info(
        "Backend encerrado."
    )
