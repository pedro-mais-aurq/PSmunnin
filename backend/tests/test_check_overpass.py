import asyncio
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import overpass_config
import pytest
from scripts import check_overpass


def test_diagnostic_shares_application_settings():
    assert check_overpass.OVERPASS_ENDPOINTS is overpass_config.OVERPASS_ENDPOINTS
    assert check_overpass.OVERPASS_TIMEOUT is overpass_config.OVERPASS_TIMEOUT
    assert check_overpass.USER_AGENT == overpass_config.USER_AGENT


@pytest.mark.parametrize("outcome,expected_status,expected_result", [
    ("ok", "200", "ok"),
    ("timeout", "timeout", "failed"),
    ("connect", "connect_error", "failed"),
    ("transport", "transport_error", "failed"),
    ("503", "503", "failed"),
    ("html", "200", "invalid_response"),
    ("remark", "200", "invalid_response"),
    ("invalid_elements", "200", "invalid_response"),
])
def test_diagnostic_uses_small_query_and_reports_safe_result(monkeypatch, outcome, expected_status, expected_result):
    def handler(request):
        assert request.method == "POST"
        assert parse_qs(request.content.decode()) == {"data": ["[out:json][timeout:5];node(1);out ids;"]}
        assert request.headers["User-Agent"] == check_overpass.USER_AGENT
        assert request.extensions["timeout"] == {"connect": 10.0, "read": 45.0, "write": 10.0, "pool": 10.0}
        if outcome == "timeout":
            raise httpx.ReadTimeout("sensitive-message", request=request)
        if outcome == "connect":
            raise httpx.ConnectError("sensitive-message", request=request)
        if outcome == "transport":
            raise httpx.RemoteProtocolError("sensitive-message", request=request)
        if outcome == "503":
            return httpx.Response(503, text="sensitive-body")
        if outcome == "html":
            return httpx.Response(200, text="<html>sensitive-body</html>")
        if outcome == "remark":
            return httpx.Response(200, json={"elements": [], "remark": "runtime error"})
        if outcome == "invalid_elements":
            return httpx.Response(200, json={"elements": [None]})
        return httpx.Response(200, json={"elements": []})

    async def run():
        async with httpx.AsyncClient(timeout=check_overpass.OVERPASS_TIMEOUT, transport=httpx.MockTransport(handler)) as client:
            times = iter([10.0, 11.25])
            monkeypatch.setattr(check_overpass, "time", SimpleNamespace(perf_counter=lambda: next(times)))
            return await check_overpass.probe_endpoint(client, "https://example.test/api")

    assert asyncio.run(run()) == {
        "endpoint": "https://example.test/api", "status": expected_status,
        "result": expected_result, "elapsed": 1.25,
    }


@pytest.mark.parametrize("has_failure", [False, True])
def test_diagnostic_checks_every_endpoint_once_even_after_success(monkeypatch, capsys, has_failure):
    real_client = httpx.AsyncClient
    calls = []
    endpoints = overpass_config.DEFAULT_OVERPASS_ENDPOINTS

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(503 if has_failure and str(request.url) == endpoints[1] else 200,
                              json={"elements": []})

    monkeypatch.setattr(check_overpass, "OVERPASS_ENDPOINTS", endpoints)
    monkeypatch.setattr(check_overpass.httpx, "AsyncClient", lambda **kwargs: real_client(
        **kwargs, transport=httpx.MockTransport(handler),
    ))
    assert asyncio.run(check_overpass.check_endpoints()) == int(has_failure)
    assert calls == list(endpoints)
    output = capsys.readouterr().out
    for endpoint in endpoints:
        assert endpoint in output
    assert output.count("elapsed=") == 3


def test_help_works_without_database_or_pipeline_imports(tmp_path):
    # Copy only the two diagnostic modules, so importing the pipeline is impossible.
    source = Path(__file__).resolve().parents[1]
    (tmp_path / "scripts").mkdir()
    (tmp_path / "overpass_config.py").write_bytes((source / "overpass_config.py").read_bytes())
    (tmp_path / "scripts/check_overpass.py").write_bytes((source / "scripts/check_overpass.py").read_bytes())
    env = os.environ.copy()
    for key in ["MONGO_URL", "DB_NAME", "OVERPASS_ENDPOINTS", "PYTHONPATH"]:
        env.pop(key, None)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_overpass", "--help"], cwd=tmp_path,
        env=env, capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Não acessa o banco" in " ".join(result.stdout.split())
