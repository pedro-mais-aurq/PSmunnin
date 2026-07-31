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
import json
import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
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

USER_AGENT = os.getenv(
    "OSM_USER_AGENT",
    "PSMunninMVP/1.0",
).strip()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

BACKGROUND_TASKS: dict[
    asyncio.Task[None],
    str,
] = {}

STALE_MONITOR_TASK: Optional[
    asyncio.Task[None]
] = None

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


class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    search_id: str
    name: str

    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    lat: Optional[float] = None
    lon: Optional[float] = None

    has_website: bool = False
    website_reachable: Optional[bool] = None
    https: Optional[bool] = None
    response_ms: Optional[int] = None

    has_title: Optional[bool] = None
    has_meta_description: Optional[bool] = None
    has_viewport: Optional[bool] = None
    has_favicon: Optional[bool] = None

    status_code: Optional[int] = None

    issues: list[str] = Field(default_factory=list)

    score: int = 0
    priority: LeadPriority = "low"

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

    error: Optional[str] = None

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
# OSM data fetch
# ---------------------------------------------------------------------------
async def geocode_region(regiao: str) -> Optional[dict]:
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


async def fetch_businesses(
    nicho: str,
    regiao: str,
    limit: int,
) -> tuple[list[dict], str]:
    """Return (list of raw business dicts, resolved region display name)."""
    region_info = await geocode_region(regiao)
    if not region_info:
        raise HTTPException(status_code=404, detail=f"Região não encontrada: {regiao}")

    filters = resolve_nicho(nicho)
    query = _build_overpass_query(filters, region_info["bbox"], limit)
    logger.info("Overpass query for %s / %s: %s", nicho, regiao, filters)

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=45) as cli:
        r = await cli.post(OVERPASS_URL, data={"data": query}, headers=headers)
        r.raise_for_status()
        data = r.json()

    elements = data.get("elements", [])
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
        phone = tags.get("phone") or tags.get("contact:phone")
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
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "http://" + url
    return url


async def analyze_website(url: str) -> dict:
    """Basic digital presence analysis. Returns dict with heuristic results."""
    url = _normalize_url(url)
    result: dict = {
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
    if not url:
        result["issues"].append("Sem site cadastrado")
        return result

    headers = {"User-Agent": USER_AGENT}
    started = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(
            timeout=10, follow_redirects=True, headers=headers
        ) as cli:
            r = await cli.get(url)
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        final_url = str(r.url)
        html = r.text[:200_000]  # cap
        result["website_reachable"] = True
        result["status_code"] = r.status_code
        result["https"] = final_url.lower().startswith("https://")
        result["response_ms"] = elapsed_ms

        # Basic HTML heuristics (regex is enough for MVP; avoids new deps)
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        result["has_title"] = bool(title_m and title_m.group(1).strip())

        desc_m = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        result["has_meta_description"] = bool(desc_m and desc_m.group(1).strip())

        viewport_m = re.search(
            r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE
        )
        result["has_viewport"] = bool(viewport_m)

        favicon_m = re.search(
            r'<link[^>]+rel=["\'](?:shortcut )?icon["\']', html, re.IGNORECASE
        )
        result["has_favicon"] = bool(favicon_m)

        if not result["https"]:
            result["issues"].append("Sem HTTPS")
        if not result["has_viewport"]:
            result["issues"].append("Não é responsivo (sem meta viewport)")
        if not result["has_title"]:
            result["issues"].append("Sem título (<title>)")
        if not result["has_meta_description"]:
            result["issues"].append("Sem meta description (SEO)")
        if not result["has_favicon"]:
            result["issues"].append("Sem favicon")
        if elapsed_ms > 3000:
            result["issues"].append(f"Site lento ({elapsed_ms}ms)")
        if r.status_code >= 400:
            result["issues"].append(f"Status HTTP {r.status_code}")
    except httpx.TimeoutException:
        result["issues"].append("Site fora do ar (timeout)")
    except Exception as exc:  # pragma: no cover
        result["issues"].append(f"Erro ao acessar site: {exc.__class__.__name__}")
    return result


def calculate_score(lead: Lead) -> tuple[int, str]:
    """Higher score = better opportunity for a web developer.

    Businesses without websites or with poor digital presence get higher scores.
    """
    if not lead.has_website:
        score = 92
    else:
        base = 25
        if not lead.website_reachable:
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
        )

        await _update_search(
            search.id,
            total_found=len(businesses),
        )

        async def process_business(
            business: dict,
        ) -> Lead:
            lead = Lead(
                search_id=search.id,
                name=business["name"],
                category=business.get("category"),
                address=business.get("address"),
                phone=business.get("phone"),
                website=business.get("website"),
                lat=business.get("lat"),
                lon=business.get("lon"),
                has_website=bool(
                    business.get("website")
                ),
            )

            if lead.has_website and lead.website:
                analysis = await analyze_website(
                    lead.website
                )

                for key, value in analysis.items():
                    setattr(lead, key, value)
            else:
                lead.issues = [
                    "Sem site cadastrado"
                ]

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

    except Exception as exc:
        logger.exception(
            "Falha inesperada no pipeline: search=%s",
            search.id,
        )

        await _update_search(
            search.id,
            status="failed",
            error=(
                "Não foi possível concluir a pesquisa. "
                f"Erro interno: {exc.__class__.__name__}."
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
