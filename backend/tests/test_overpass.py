import asyncio
import importlib
import logging
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import HTTPException

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "psmunnin_test")
server = importlib.import_module("server")

SEARCH_ID = "2c7686cf-57c5-4dc6-ad10-ea3e25940a14"
QUERY = '[out:json];node["amenity"="dentist"];out;'
PRIMARY, BACKUP = server.DEFAULT_OVERPASS_ENDPOINTS
VALID_DATA = {"elements": [{"type": "node", "tags": {"name": "Clínica Teste"}}]}


@pytest.fixture
def overpass_http(monkeypatch):
    """Every HTTP request is mocked, including accidental unexpected requests."""
    real_client = httpx.AsyncClient
    calls = []
    options = []
    sleep = AsyncMock()
    monkeypatch.setattr(server, "OVERPASS_ENDPOINTS", (PRIMARY, BACKUP))
    monkeypatch.setattr(server.asyncio, "sleep", sleep)

    def install(handler):
        def record(request):
            calls.append(str(request.url))
            assert request.method == "POST"
            assert request.headers["user-agent"] == server.USER_AGENT
            assert request.headers["accept"] == "application/json"
            assert request.extensions["timeout"] == {
                "connect": 10.0, "read": 45.0, "write": 10.0, "pool": 10.0,
            }
            return handler(request)

        def client_factory(*args, **kwargs):
            options.append(kwargs.copy())
            return real_client(*args, **kwargs, transport=httpx.MockTransport(record))

        monkeypatch.setattr(server.httpx, "AsyncClient", client_factory)

    return SimpleNamespace(install=install, calls=calls, options=options, sleep=sleep)


def test_primary_success_does_not_call_backup(overpass_http, caplog):
    def handler(request):
        assert parse_qs(request.content.decode())["data"] == [QUERY]
        return httpx.Response(200, json=VALID_DATA)

    overpass_http.install(handler)
    with caplog.at_level(logging.INFO, logger="ps-munnin"):
        result = asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID))

    assert result == VALID_DATA
    assert overpass_http.calls == [PRIMARY]
    overpass_http.sleep.assert_not_awaited()
    for record in caplog.records:
        if record.name == "ps-munnin":
            message = record.getMessage()
            for field in (SEARCH_ID, "provider=overpass", f"endpoint={PRIMARY}", "attempt=1", "result="):
                assert field in message
    assert "status=200 elements=1" in caplog.text


@pytest.mark.parametrize("error_type", [
    httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
    httpx.WriteTimeout, httpx.PoolTimeout, httpx.ReadError,
    httpx.WriteError, httpx.RemoteProtocolError,
])
def test_network_failure_fails_over(overpass_http, error_type, caplog):
    def handler(request):
        if str(request.url) == PRIMARY:
            raise error_type("mock network failure", request=request)
        return httpx.Response(200, json=VALID_DATA)

    overpass_http.install(handler)
    result = asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID))

    assert result == VALID_DATA
    assert overpass_http.calls == [PRIMARY, BACKUP]
    overpass_http.sleep.assert_not_awaited()
    assert SEARCH_ID in caplog.text
    assert f"error_type={error_type.__name__}" in caplog.text
    assert any(record.exc_info for record in caplog.records)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_temporary_http_fails_over(overpass_http, status, caplog):
    def handler(request):
        if str(request.url) == PRIMARY:
            return httpx.Response(status, text="temporary failure")
        return httpx.Response(200, json=VALID_DATA)

    overpass_http.install(handler)
    assert asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID)) == VALID_DATA
    assert overpass_http.calls == [PRIMARY, BACKUP]
    assert f"status={status}" in caplog.text
    overpass_http.sleep.assert_not_awaited()


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<html>Unavailable</html>"),
    httpx.Response(200, content=b""),
    httpx.Response(200, json=[]),
    httpx.Response(200, json=None),
    httpx.Response(200, json={}),
    httpx.Response(200, json={"elements": {}}),
    httpx.Response(200, json={"elements": [None]}),
    httpx.Response(200, json={"elements": [], "remark": "runtime error: timed out"}),
])
def test_invalid_response_fails_over(overpass_http, response, caplog):
    overpass_http.install(lambda request: response if str(request.url) == PRIMARY
                          else httpx.Response(200, json=VALID_DATA))
    assert asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID)) == VALID_DATA
    assert overpass_http.calls == [PRIMARY, BACKUP]
    assert "result=invalid_response" in caplog.text


def test_valid_empty_result_is_success(overpass_http):
    overpass_http.install(lambda request: httpx.Response(200, json={"elements": []}))
    assert asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID)) == {"elements": []}
    assert overpass_http.calls == [PRIMARY]


@pytest.mark.parametrize("failure", ["network", "http", "invalid"])
def test_all_endpoints_fail_with_controlled_503(overpass_http, failure, caplog):
    def handler(request):
        if failure == "network":
            raise httpx.ConnectError("mock network failure", request=request)
        if failure == "http":
            return httpx.Response(503)
        return httpx.Response(200, text="<html>error</html>")

    overpass_http.install(handler)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID))

    assert overpass_http.calls == [PRIMARY, BACKUP, PRIMARY, BACKUP]
    overpass_http.sleep.assert_awaited_once_with(1.5)
    assert caught.value.status_code == 503
    assert caught.value.detail == server.OVERPASS_UNAVAILABLE_ERROR
    assert caught.value.__cause__ is not None
    assert "ConnectError" not in caught.value.detail
    assert "overpass" not in caught.value.detail.lower()
    assert "All Overpass endpoints failed" in caplog.text
    assert "attempt=4 round=2" in caplog.text


def test_second_round_succeeds_after_single_backoff(overpass_http):
    def handler(request):
        if len(overpass_http.calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=VALID_DATA)

    overpass_http.install(handler)
    assert asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID)) == VALID_DATA
    assert overpass_http.calls == [PRIMARY, BACKUP, PRIMARY]
    overpass_http.sleep.assert_awaited_once_with(1.5)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 302])
def test_rejected_request_is_not_retried_or_masked(overpass_http, status, caplog):
    body = '<p>line 4: parse error: token="secret-example" email=private@example.test</p>'
    overpass_http.install(lambda request: httpx.Response(status, text=body))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID))

    assert caught.value.status_code == 502
    assert "rejeitou a consulta" in caught.value.detail
    assert "temporariamente indisponíveis" not in caught.value.detail
    assert overpass_http.calls == [PRIMARY]
    overpass_http.sleep.assert_not_awaited()
    assert f"status={status}" in caplog.text
    assert "line 4: parse error" in caplog.text
    for private_value in ("secret-example", "private@example.test"):
        assert private_value not in caplog.text
        assert private_value not in caught.value.detail


def test_cancellation_is_not_retried(overpass_http):
    def handler(request):
        raise asyncio.CancelledError()

    overpass_http.install(handler)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID))
    assert overpass_http.calls == [PRIMARY]
    overpass_http.sleep.assert_not_awaited()


def test_endpoint_configuration_defaults_and_trimming():
    assert server._parse_overpass_endpoints(None) == (PRIMARY, BACKUP)
    assert server._parse_overpass_endpoints(f" , {BACKUP},, {PRIMARY}, {BACKUP}, ") == (BACKUP, PRIMARY)
    assert server._parse_overpass_endpoints(BACKUP) == (BACKUP,)


@pytest.mark.parametrize("value", [
    "", " , , ", "not-a-url", "ftp://example.test/api", "https://",
    "https://user:secret@example.test/api", "https://example.test/api?token=secret",
    "https://example.test/api#secret", "https://example.test:bad/api",
    "https://exa mple.test/api", "https://[invalid/api",
])
def test_invalid_endpoint_configuration_is_rejected_without_echoing(value):
    with pytest.raises(RuntimeError, match="OVERPASS_ENDPOINTS") as caught:
        server._parse_overpass_endpoints(value)
    assert "secret" not in str(caught.value)


def test_configured_pool_order_is_used(overpass_http, monkeypatch):
    monkeypatch.setattr(server, "OVERPASS_ENDPOINTS", (BACKUP,))
    overpass_http.install(lambda request: httpx.Response(503))
    with pytest.raises(HTTPException):
        asyncio.run(server.query_overpass(QUERY, search_id=SEARCH_ID))
    assert overpass_http.calls == [BACKUP, BACKUP]


def test_fetch_businesses_propagates_search_id(monkeypatch):
    geocode = AsyncMock(return_value={
        "bbox": ["-20", "-19", "-44", "-43"], "display_name": "Belo Horizonte",
    })
    query = AsyncMock(return_value={"elements": [
        {"tags": {"name": "Clínica Teste", "contact:phone": "+55 31 3333-3333"}},
        {"tags": {"name": "Clínica Teste"}},
        {"tags": {}},
    ]})
    monkeypatch.setattr(server, "geocode_region", geocode)
    monkeypatch.setattr(server, "query_overpass", query)

    businesses, region = asyncio.run(server.fetch_businesses(
        "dentistas", "Belo Horizonte", 10, search_id=SEARCH_ID,
    ))

    geocode.assert_awaited_once_with("Belo Horizonte")
    assert query.await_args.kwargs == {"search_id": SEARCH_ID}
    assert '(\nnode["amenity"="dentist"]' in query.await_args.args[0]
    assert len(businesses) == 1
    assert businesses[0]["contacts"]["phone"] == ["+55 31 3333-3333"]
    assert region == "Belo Horizonte"


@pytest.mark.parametrize("failure", [False, True])
def test_pipeline_persists_outcome_and_closes_heartbeat(monkeypatch, overpass_http, failure):
    """Exercise the real pipeline -> collection -> Overpass path without MongoDB/network."""
    search = server.Search(id=SEARCH_ID, nicho="dentistas", regiao="Belo Horizonte")
    updates = []
    stops = []

    async def update(search_id, **fields):
        assert search_id == SEARCH_ID
        updates.append(fields)

    async def heartbeat(search_id, stop):
        assert search_id == SEARCH_ID
        await stop.wait()
        stops.append(stop.is_set())

    def handler(request):
        if failure:
            raise httpx.ConnectError("mock network failure", request=request)
        return httpx.Response(200, json=VALID_DATA)

    overpass_http.install(handler)
    monkeypatch.setattr(server, "_update_search", update)
    monkeypatch.setattr(server, "_search_heartbeat", heartbeat)
    monkeypatch.setattr(server, "geocode_region", AsyncMock(return_value={
        "bbox": ["-20", "-19", "-44", "-43"], "display_name": "Belo Horizonte",
    }))
    detection = AsyncMock(return_value={"website_status": "not_found"})
    monkeypatch.setattr(server, "detect_website", detection)
    leads = SimpleNamespace(delete_many=AsyncMock(), insert_many=AsyncMock())
    monkeypatch.setattr(server, "db", SimpleNamespace(leads=leads))

    asyncio.run(server.run_pipeline(search, 10))

    assert updates[0] == {"status": "running", "error": None}
    assert stops == [True]
    if failure:
        assert updates[1:] == [{"status": "failed", "error": server.OVERPASS_UNAVAILABLE_ERROR}]
        assert all("total_found" not in item for item in updates)
        detection.assert_not_awaited()
        leads.delete_many.assert_not_awaited()
        leads.insert_many.assert_not_awaited()
    else:
        assert updates[1] == {"total_found": 1}
        assert updates[2] == {"status": "done", "total_analyzed": 1, "error": None}
        leads.delete_many.assert_awaited_once_with({"search_id": SEARCH_ID})
        assert leads.insert_many.await_args.args[0][0]["search_id"] == SEARCH_ID


def test_pipeline_passes_search_id_to_collection(monkeypatch):
    search = server.Search(id=SEARCH_ID, nicho="dentistas", regiao="Belo Horizonte")
    fetch = AsyncMock(side_effect=HTTPException(status_code=503, detail="Tente novamente."))
    monkeypatch.setattr(server, "fetch_businesses", fetch)
    monkeypatch.setattr(server, "_update_search", AsyncMock())
    monkeypatch.setattr(server, "_search_heartbeat", AsyncMock())

    asyncio.run(server.run_pipeline(search, 10))

    fetch.assert_awaited_once_with("dentistas", "Belo Horizonte", 10, search_id=SEARCH_ID)


def test_real_heartbeat_runs_during_overpass_backoff(monkeypatch, overpass_http):
    async def run():
        stop = asyncio.Event()
        update = AsyncMock(side_effect=lambda *args, **kwargs: stop.set())
        monkeypatch.setattr(server, "_update_search", update)
        monkeypatch.setattr(server, "SEARCH_HEARTBEAT_SECONDS", 0.001)

        async def backoff(_seconds):
            await asyncio.wait_for(stop.wait(), timeout=1.0)

        overpass_http.sleep.side_effect = backoff
        overpass_http.install(lambda request: httpx.Response(503) if len(overpass_http.calls) < 3
                              else httpx.Response(200, json={"elements": []}))
        task = asyncio.create_task(server._search_heartbeat(SEARCH_ID, stop))
        try:
            await server.query_overpass(QUERY, search_id=SEARCH_ID)
        finally:
            stop.set()
            await task
        update.assert_awaited_once_with(SEARCH_ID)

    asyncio.run(run())
