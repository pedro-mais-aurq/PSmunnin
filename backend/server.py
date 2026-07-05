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
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import difflib
import re
import unicodedata
from fastapi import HTTPException


import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="PS Munnin API", version="0.1.0")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ps-munnin")

USER_AGENT = "PSMunninMVP/1.0 (contact: dev@psmunnin.local)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


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


def _normalize(text: str) -> str:
    """Lowercase + strip accents for keyword matching."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


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
class SearchCreate(BaseModel):
    nicho: str = Field(min_length=2, max_length=80)
    regiao: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=25, ge=1, le=60)


class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    search_id: str
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    # analysis
    has_website: bool = False
    website_reachable: Optional[bool] = None
    https: Optional[bool] = None
    response_ms: Optional[int] = None
    has_title: Optional[bool] = None
    has_meta_description: Optional[bool] = None
    has_viewport: Optional[bool] = None
    has_favicon: Optional[bool] = None
    status_code: Optional[int] = None
    issues: List[str] = Field(default_factory=list)
    score: int = 0
    priority: str = "low"  # low | medium | high
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Search(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nicho: str
    regiao: str
    status: str = "pending"  # pending | running | done | failed
    total_found: int = 0
    total_analyzed: int = 0
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContactMessage(BaseModel):
    subject: str
    body: str
    channel: str  # email | whatsapp | generic


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
    doc = {k: v for k, v in doc.items() if k != "_id"}
    for k in ("created_at", "updated_at"):
        if isinstance(doc.get(k), str):
            doc[k] = datetime.fromisoformat(doc[k])
    return Search(**doc)


def _deserialize_lead(doc: dict) -> Lead:
    doc = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return Lead(**doc)


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


async def fetch_businesses(nicho: str, regiao: str, limit: int) -> tuple[list[dict], Optional[str]]:
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
        if not name or name in seen_names:
            continue
        seen_names.add(name)
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
async def run_pipeline(search: Search, limit: int) -> None:
    """Fetch businesses, analyze, store leads, update search status."""
    try:
        await db.searches.update_one(
            {"id": search.id},
            {"$set": {"status": "running", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        businesses, _ = await fetch_businesses(search.nicho, search.regiao, limit)
        await db.searches.update_one(
            {"id": search.id}, {"$set": {"total_found": len(businesses)}}
        )

        # analyze in parallel batches
        async def _process(b: dict) -> Lead:
            lead = Lead(
                search_id=search.id,
                name=b["name"],
                category=b.get("category"),
                address=b.get("address"),
                phone=b.get("phone"),
                website=b.get("website"),
                lat=b.get("lat"),
                lon=b.get("lon"),
                has_website=bool(b.get("website")),
            )
            if lead.has_website:
                analysis = await analyze_website(lead.website)
                for k, v in analysis.items():
                    setattr(lead, k, v)
            else:
                lead.issues = ["Sem site cadastrado"]
            score, priority = calculate_score(lead)
            lead.score = score
            lead.priority = priority
            return lead

        # limit concurrency to be a good citizen
        sem = asyncio.Semaphore(6)

        async def _bounded(b: dict) -> Lead:
            async with sem:
                return await _process(b)

        leads = await asyncio.gather(*[_bounded(b) for b in businesses])
        # sort by score desc
        leads.sort(key=lambda x: x.score, reverse=True)

        if leads:
            await db.leads.insert_many([_serialize(lead) for lead in leads])

        await db.searches.update_one(
            {"id": search.id},
            {
                "$set": {
                    "status": "done",
                    "total_analyzed": len(leads),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        logger.info(
            "Pipeline done: search=%s found=%d analyzed=%d",
            search.id,
            len(businesses),
            len(leads),
        )
    except HTTPException as exc:
        await db.searches.update_one(
            {"id": search.id},
            {"$set": {"status": "failed", "error": exc.detail}},
        )
    except Exception as exc:
        logger.exception("Pipeline failed")
        await db.searches.update_one(
            {"id": search.id},
            {"$set": {"status": "failed", "error": str(exc)}},
        )


# ---------------------------------------------------------------------------
# Contact message template
# ---------------------------------------------------------------------------
def build_message(lead: Lead, channel: str = "email") -> ContactMessage:
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
    return {"service": "PS Munnin API", "status": "ok"}


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.post("/searches", response_model=Search)
async def create_search(payload: SearchCreate):
    search = Search(nicho=payload.nicho.strip(), regiao=payload.regiao.strip())
    await db.searches.insert_one(_serialize(search))
    # Run pipeline in background so the request returns fast
    asyncio.create_task(run_pipeline(search, payload.limit))
    return search


@api_router.get("/searches", response_model=List[Search])
async def list_searches():
    docs = await db.searches.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [_deserialize_search(d) for d in docs]


@api_router.get("/searches/{search_id}")
async def get_search(search_id: str):
    doc = await db.searches.find_one({"id": search_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada")
    search = _deserialize_search(doc)
    lead_docs = await db.leads.find({"search_id": search_id}, {"_id": 0}).sort("score", -1).to_list(500)
    leads = [_deserialize_lead(d) for d in lead_docs]
    return {"search": search, "leads": leads}


@api_router.delete("/searches/{search_id}")
async def delete_search(search_id: str):
    res = await db.searches.delete_one({"id": search_id})
    await db.leads.delete_many({"search_id": search_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada")
    return {"ok": True}


@api_router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str):
    doc = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return _deserialize_lead(doc)


@api_router.get("/leads/{lead_id}/message", response_model=ContactMessage)
async def generate_message(lead_id: str, channel: str = "email"):
    doc = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    lead = _deserialize_lead(doc)
    return build_message(lead, channel=channel)


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
