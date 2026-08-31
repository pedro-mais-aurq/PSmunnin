import asyncio
import importlib
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault(
    "MONGO_URL",
    "mongodb://localhost:27017",
)

os.environ.setdefault(
    "DB_NAME",
    "psmunnin_test",
)

server = importlib.import_module("server")


def test_search_create_strips_text():
    payload = server.SearchCreate(
        nicho="  dentistas  ",
        regiao="  Belo Horizonte  ",
        limit=10,
    )

    assert payload.nicho == "dentistas"
    assert payload.regiao == "Belo Horizonte"
    assert payload.limit == 10


def test_resolve_nicho_accepts_alias():
    tags = server.resolve_nicho(
        "odontologia"
    )

    assert (
        "amenity",
        "dentist",
    ) in tags


def test_resolve_nicho_rejects_unknown_value():
    with pytest.raises(
        HTTPException
    ) as captured:
        server.resolve_nicho(
            "nicho inexistente xyz"
        )

    assert captured.value.status_code == 400

    assert isinstance(
        captured.value.detail,
        dict,
    )

    assert (
        "supported_niches"
        in captured.value.detail
    )


def test_score_without_website_is_high():
    lead = server.Lead(
        search_id="search-1",
        name="Empresa sem site",
        has_website=False,
        website_status="not_found",
    )

    assert server.calculate_score(
        lead
    ) == (
        92,
        "high",
    )


def test_score_for_weak_website_is_capped():
    lead = server.Lead(
        search_id="search-1",
        name="Empresa com site fraco",
        website="http://example.com",
        has_website=True,
        website_reachable=True,
        https=False,
        has_viewport=False,
        has_title=False,
        has_meta_description=False,
        has_favicon=False,
        response_ms=4_000,
        status_code=500,
        website_status="confirmed",
    )

    assert server.calculate_score(
        lead
    ) == (
        95,
        "high",
    )


def test_error_detail_is_normalized():
    result = server._format_error_detail(
        {
            "message": "Nicho não suportado.",
            "supported_niches": [
                "dentista",
                "restaurante",
            ],
        }
    )

    assert (
        "Nicho não suportado."
        in result
    )

    assert "dentista" in result
    assert "restaurante" in result


def test_email_message_contains_lead_name():
    lead = server.Lead(
        search_id="search-1",
        name="Clínica Teste",
        issues=[
            "Sem site cadastrado",
        ],
    )

    message = server.build_message(
        lead,
        channel="email",
    )

    assert message.channel == "email"
    assert "Clínica Teste" in message.subject
    assert "Clínica Teste" in message.body


def test_whatsapp_message_differs_from_email():
    lead = server.Lead(
        search_id="search-1",
        name="Empresa Teste",
        issues=[
            "Sem HTTPS",
        ],
    )

    email_message = server.build_message(
        lead,
        channel="email",
    )

    whatsapp_message = server.build_message(
        lead,
        channel="whatsapp",
    )

    assert (
        email_message.body
        != whatsapp_message.body
    )

    assert (
        whatsapp_message.channel
        == "whatsapp"
    )


def test_deserialize_search_normalizes_legacy_error_object():
    document = {
        "id": "search-legacy",
        "nicho": "dentistas",
        "regiao": "Belo Horizonte",
        "status": "failed",
        "total_found": 0,
        "total_analyzed": 0,
        "error": {
            "message": "Nicho não suportado.",
            "supported_niches": [
                "dentista",
                "restaurante",
            ],
        },
        "created_at": (
            "2026-07-31T12:00:00+00:00"
        ),
        "updated_at": (
            "2026-07-31T12:00:01+00:00"
        ),
    }

    search = server._deserialize_search(
        document
    )

    assert isinstance(
        search.error,
        str,
    )

    assert (
        "Nicho não suportado."
        in search.error
    )

    assert "dentista" in search.error


def test_fail_stale_searches_uses_age_filter(
    monkeypatch,
):
    class FakeUpdateResult:
        modified_count = 2

    class FakeSearchCollection:
        def __init__(self):
            self.query = None
            self.update = None

        async def update_many(
            self,
            query,
            update,
        ):
            self.query = query
            self.update = update

            return FakeUpdateResult()

    class FakeDatabase:
        def __init__(self):
            self.searches = (
                FakeSearchCollection()
            )

    fake_database = FakeDatabase()

    monkeypatch.setattr(
        server,
        "db",
        fake_database,
    )

    modified_count = asyncio.run(
        server._fail_stale_searches()
    )

    assert modified_count == 2

    query = (
        fake_database
        .searches
        .query
    )

    assert (
        query["status"]
        == {
            "$in": [
                "pending",
                "running",
            ]
        }
    )

    assert "$lt" in query["updated_at"]

    update_fields = (
        fake_database
        .searches
        .update["$set"]
    )

    assert (
        update_fields["status"]
        == "failed"
    )

    assert (
        update_fields["error"]
        == server.INTERRUPTED_SEARCH_ERROR
    )


def test_forget_background_task_removes_mapping():
    async def fake_task_body():
        return None

    async def run_test():
        task = asyncio.create_task(
            fake_task_body()
        )

        server.BACKGROUND_TASKS[
            task
        ] = "search-1"

        await task

        server._forget_background_task(
            task
        )

        assert (
            task
            not in server.BACKGROUND_TASKS
        )

    asyncio.run(run_test())
