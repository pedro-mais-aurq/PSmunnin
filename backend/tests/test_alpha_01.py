import asyncio
import importlib
import os
import socket

import httpx
import pytest

os.environ.setdefault(
    "MONGO_URL",
    "mongodb://localhost:27017",
)
os.environ.setdefault(
    "DB_NAME",
    "psmunnin_test",
)

server = importlib.import_module("server")


VALID_HTML = """
<html>
  <head>
    <title>Empresa Exemplo</title>
    <meta name="description" content="Descrição">
    <meta name="viewport" content="width=device-width">
    <link rel="icon" href="/favicon.ico">
  </head>
</html>
"""


def _run(coroutine):
    return asyncio.run(coroutine)


def _install_http_handler(monkeypatch, handler):
    real_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    client_options = []

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        client_options.append(dict(kwargs))
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        server.httpx,
        "AsyncClient",
        client_factory,
    )

    def public_getaddrinfo(
        _hostname,
        port,
        _family=0,
        _socket_type=0,
    ):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            )
        ]

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        public_getaddrinfo,
    )

    return client_options


def _ok_handler(request):
    return httpx.Response(
        200,
        text=VALID_HTML,
        request=request,
    )


def _detect(tags, **kwargs):
    return _run(
        server.detect_website(
            tags,
            contacts=server.extract_contacts(tags),
            business_name="Empresa Exemplo",
            region="Belo Horizonte, MG",
            **kwargs,
        )
    )


def _reachable_probe(url="https://empresaexemplo.com.br"):
    result = server._empty_website_analysis()
    result.update(
        {
            "outcome": "reachable",
            "url": url,
            "website_reachable": True,
            "https": url.startswith("https://"),
            "status_code": 200,
        }
    )
    return result


def test_valid_website_tag(monkeypatch):
    _install_http_handler(monkeypatch, _ok_handler)

    result = _detect(
        {"website": "empresaexemplo.com.br"}
    )

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "osm_website"
    assert result["website_reachable"] is True


def test_valid_contact_website_tag(monkeypatch):
    _install_http_handler(monkeypatch, _ok_handler)

    result = _detect(
        {"contact:website": "empresaexemplo.com.br"}
    )

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "osm_contact_website"


def test_valid_url_tag(monkeypatch):
    _install_http_handler(monkeypatch, _ok_handler)

    result = _detect(
        {"url": "https://empresaexemplo.com.br"}
    )

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "osm_url"


def test_instagram_without_website(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        False,
    )
    tags = {"website": "instagram.com/empresaexemplo"}

    result = _detect(tags)
    contacts = server.extract_contacts(tags)

    assert result["website_status"] == "unknown"
    assert result["website"] is None
    assert contacts.instagram == [
        "https://www.instagram.com/empresaexemplo/"
    ]


def test_facebook_without_website(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        False,
    )
    tags = {"website": "facebook.com/empresaexemplo"}

    result = _detect(tags)
    contacts = server.extract_contacts(tags)

    assert result["website_status"] == "unknown"
    assert result["website"] is None
    assert contacts.facebook == [
        "https://www.facebook.com/empresaexemplo"
    ]


def test_website_with_redirect(monkeypatch):
    def redirect_handler(request):
        if request.headers["Host"] == "empresaexemplo.com.br":
            return httpx.Response(
                301,
                headers={
                    "Location": (
                        "https://www.empresaexemplo.com.br/"
                    )
                },
                request=request,
            )

        return _ok_handler(request)

    _install_http_handler(monkeypatch, redirect_handler)

    result = _detect(
        {"website": "empresaexemplo.com.br"}
    )

    assert result["website_reachable"] is True
    assert result["website"] == (
        "https://www.empresaexemplo.com.br/"
    )


def test_https_is_tried_first(monkeypatch):
    requested_schemes = []

    def handler(request):
        requested_schemes.append(request.url.scheme)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _detect(
        {"website": "empresaexemplo.com.br"}
    )

    assert requested_schemes == ["https"]
    assert result["https"] is True


def test_http_fallback(monkeypatch):
    requested_schemes = []

    def handler(request):
        requested_schemes.append(request.url.scheme)

        if request.url.scheme == "https":
            raise httpx.ConnectError(
                "TLS indisponível",
                request=request,
            )

        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _detect(
        {"website": "empresaexemplo.com.br"}
    )

    assert requested_schemes == ["https", "http"]
    assert result["website_reachable"] is True
    assert result["https"] is False


def test_website_returning_403(monkeypatch):
    def handler(request):
        return httpx.Response(
            403,
            request=request,
        )

    _install_http_handler(monkeypatch, handler)

    result = _detect(
        {"website": "empresaexemplo.com.br"}
    )

    assert result["website_status"] == "confirmed"
    assert result["website_reachable"] is False
    assert result["status_code"] == 403


def test_website_timeout_is_not_not_found(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    _install_http_handler(monkeypatch, handler)

    result = _detect(
        {"website": "empresaexemplo.com.br"}
    )

    assert result["website_status"] == "confirmed"
    assert result["website_reachable"] is False
    assert "Verificação do site expirou" in result["issues"]


@pytest.mark.parametrize(
    "private_url",
    [
        "http://127.0.0.1",
        "http://192.168.1.10",
    ],
)
def test_detect_website_does_not_confirm_private_tag(
    monkeypatch,
    private_url,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _detect({"website": private_url})

    assert result["website_status"] == "unknown"
    assert result["has_website"] is False
    assert result["website"] is None
    assert result["website_reachable"] is None
    assert result["website_source"] is None
    assert requests == []


@pytest.mark.parametrize(
    "private_redirect",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.10/admin",
    ],
)
def test_detect_website_does_not_confirm_private_redirect(
    monkeypatch,
    private_redirect,
):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            302,
            headers={"Location": private_redirect},
            request=request,
        )

    _install_http_handler(monkeypatch, handler)

    result = _detect(
        {"website": "https://public.example.com"}
    )

    assert result["website_status"] == "unknown"
    assert result["has_website"] is False
    assert result["website"] is None
    assert result["website_reachable"] is None
    assert result["website_source"] is None
    assert len(requests) == 1
    assert requests[0].url.host == "93.184.216.34"
    assert requests[0].headers["Host"] == (
        "public.example.com"
    )


def test_corporate_email_domain(monkeypatch):
    _install_http_handler(monkeypatch, _ok_handler)

    result = _detect(
        {"email": "contato@empresaexemplo.com.br"}
    )

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "email_domain"
    assert result["website"] == (
        "https://empresaexemplo.com.br"
    )


def test_unsafe_email_domain_is_ignored_for_safe_candidate(
    monkeypatch,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _detect(
        {
            "contact:email": (
                "contato@127.0.0.1; "
                "contato@empresaexemplo.com.br"
            )
        }
    )

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "email_domain"
    assert result["website"] == (
        "https://empresaexemplo.com.br"
    )
    assert len(requests) == 1
    assert requests[0].headers["Host"] == (
        "empresaexemplo.com.br"
    )


def test_only_unsafe_email_candidate_is_unknown(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    async def fake_search(_name, _region):
        return []

    monkeypatch.setattr(
        server,
        "search_web_for_website",
        fake_search,
    )

    result = _detect(
        {"contact:email": "contato@127.0.0.1"}
    )

    assert result["website_status"] == "unknown"
    assert result["has_website"] is False
    assert result["website"] is None


def test_gmail_is_ignored_as_corporate_domain(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        False,
    )

    result = _detect(
        {"email": "empresaexemplo@gmail.com"}
    )

    assert result["website_status"] == "unknown"
    assert result["website"] is None


def test_complementary_search_finds_site(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    async def fake_search(_name, _region):
        return [
            {
                "url": "https://empresaexemplo.com.br",
                "title": "Empresa Exemplo — Site oficial",
            }
        ]

    async def fake_probe(_url):
        return _reachable_probe()

    monkeypatch.setattr(
        server,
        "search_web_for_website",
        fake_search,
    )
    monkeypatch.setattr(
        server,
        "_probe_website",
        fake_probe,
    )

    result = _detect({})

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "web_search"


def test_unsafe_search_candidate_is_ignored_for_safe_result(
    monkeypatch,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    async def fake_search(_name, _region):
        return [
            {
                "url": "http://127.0.0.1/internal",
                "title": "Empresa Exemplo — Site oficial",
            },
            {
                "url": "https://empresaexemplo.com.br",
                "title": "Empresa Exemplo — Site oficial",
            },
        ]

    monkeypatch.setattr(
        server,
        "search_web_for_website",
        fake_search,
    )

    result = _detect({})

    assert result["website_status"] == "confirmed"
    assert result["website_source"] == "web_search"
    assert result["website"] == (
        "https://empresaexemplo.com.br"
    )
    assert len(requests) == 1
    assert requests[0].headers["Host"] == (
        "empresaexemplo.com.br"
    )


def test_only_unsafe_search_candidate_is_unknown(
    monkeypatch,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    async def fake_search(_name, _region):
        return [
            {
                "url": "http://127.0.0.1/internal",
                "title": "Empresa Exemplo — Site oficial",
            }
        ]

    monkeypatch.setattr(
        server,
        "search_web_for_website",
        fake_search,
    )

    result = _detect({})

    assert result["website_status"] == "unknown"
    assert result["has_website"] is False
    assert result["website"] is None
    assert requests == []


def test_complementary_search_without_results(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    async def fake_search(_name, _region):
        return []

    monkeypatch.setattr(
        server,
        "search_web_for_website",
        fake_search,
    )

    result = _detect({})

    assert result["website_status"] == "not_found"
    assert result["website"] is None


def test_complementary_search_unavailable(monkeypatch):
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    async def fake_search(_name, _region):
        return None

    monkeypatch.setattr(
        server,
        "search_web_for_website",
        fake_search,
    )

    result = _detect({})

    assert result["website_status"] == "unknown"
    assert result["website"] is None


def test_single_phone():
    contacts = server.extract_contacts(
        {"phone": "+55 31 3333-4444"}
    )

    assert contacts.phone == ["+55 31 3333-4444"]


def test_multiple_phones():
    contacts = server.extract_contacts(
        {
            "phone": (
                "+55 31 3333-4444; "
                "+55 31 3333-5555"
            )
        }
    )

    assert contacts.phone == [
        "+55 31 3333-4444",
        "+55 31 3333-5555",
    ]


def test_duplicate_phone():
    contacts = server.extract_contacts(
        {
            "phone": "+55 31 3333-4444",
            "contact:phone": (
                "+55 31 3333-4444"
            ),
        }
    )

    assert contacts.phone == ["+55 31 3333-4444"]


def test_whatsapp_contact():
    contacts = server.extract_contacts(
        {"contact:whatsapp": "+55 31 99999-8888"}
    )

    assert contacts.whatsapp == [
        "+55 31 99999-8888"
    ]


def test_email_contact():
    contacts = server.extract_contacts(
        {"contact:email": "contato@empresa.com.br"}
    )

    assert contacts.email == [
        "contato@empresa.com.br"
    ]


def test_instagram_contact():
    contacts = server.extract_contacts(
        {"instagram": "@empresaexemplo"}
    )

    assert contacts.instagram == [
        "https://www.instagram.com/empresaexemplo/"
    ]


def test_facebook_contact():
    contacts = server.extract_contacts(
        {"contact:facebook": "empresaexemplo"}
    )

    assert contacts.facebook == [
        "https://www.facebook.com/empresaexemplo"
    ]


def test_linkedin_contact():
    contacts = server.extract_contacts(
        {"linkedin": "empresaexemplo"}
    )

    assert contacts.linkedin == [
        "https://www.linkedin.com/company/empresaexemplo/"
    ]


def test_unusual_social_value_is_preserved():
    contacts = server.extract_contacts(
        {"instagram": "perfil com espaço"}
    )

    assert contacts.instagram == ["perfil com espaço"]


def test_legacy_record_with_website():
    lead = server._deserialize_lead(
        {
            "id": "lead-old-1",
            "search_id": "search-1",
            "name": "Empresa antiga",
            "website": "https://empresa.com.br",
            "has_website": True,
        }
    )

    assert lead.website_status == "confirmed"
    assert lead.contacts == server.ContactInfo()


def test_legacy_record_without_website():
    lead = server._deserialize_lead(
        {
            "id": "lead-old-2",
            "search_id": "search-1",
            "name": "Empresa antiga",
            "has_website": False,
        }
    )

    assert lead.website_status == "unknown"
    assert lead.contacts == server.ContactInfo()


def test_score_for_confirmed_website():
    lead = server.Lead(
        search_id="search-1",
        name="Empresa com site",
        website="https://empresa.com.br",
        has_website=True,
        website_reachable=True,
        website_status="confirmed",
    )

    assert server.calculate_score(lead) == (25, "low")


def test_score_for_not_found_website():
    lead = server.Lead(
        search_id="search-1",
        name="Empresa sem site",
        website_status="not_found",
    )

    assert server.calculate_score(lead) == (92, "high")


def test_score_for_unknown_website():
    lead = server.Lead(
        search_id="search-1",
        name="Empresa inconclusiva",
        website_status="unknown",
    )

    assert server.calculate_score(lead) == (50, "medium")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://localhost",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://169.254.169.254",
        "http://0.0.0.0",
        "http://[::1]",
    ],
)
def test_ssrf_rejects_non_global_destinations(
    monkeypatch,
    url,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _run(server._probe_website(url))

    assert result["outcome"] == "unsafe"
    assert requests == []


def test_ssrf_rejects_private_dns_resolution(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    def private_getaddrinfo(
        _hostname,
        port,
        _family=0,
        _socket_type=0,
    ):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("10.0.0.25", port),
            )
        ]

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        private_getaddrinfo,
    )

    result = _run(
        server._probe_website(
            "https://public.example.com"
        )
    )

    assert result["outcome"] == "unsafe"
    assert requests == []


def test_ssrf_redirect_to_private_destination(monkeypatch):
    requested_hosts = []

    def handler(request):
        requested_hosts.append(request.headers["Host"])
        return httpx.Response(
            302,
            headers={
                "Location": "http://192.168.1.10/admin"
            },
            request=request,
        )

    _install_http_handler(monkeypatch, handler)

    result = _run(
        server._probe_website(
            "https://public.example.com"
        )
    )

    assert result["outcome"] == "unsafe"
    assert requested_hosts == ["public.example.com"]


def test_ssrf_rejects_url_credentials(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _run(
        server._probe_website(
            "https://user:password@public.example.com"
        )
    )

    assert result["outcome"] == "unsafe"
    assert requests == []


def test_ssrf_accepts_public_hostname(monkeypatch):
    requested_hosts = []

    def handler(request):
        requested_hosts.append(request.headers["Host"])
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _run(
        server._probe_website(
            "https://public.example.com"
        )
    )

    assert result["outcome"] == "reachable"
    assert requested_hosts == ["public.example.com"]


def test_ssrf_accepts_public_redirect(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)

        if request.headers["Host"] == "public.example.com":
            return httpx.Response(
                302,
                headers={
                    "Location": (
                        "https://www.public.example.com/site"
                    )
                },
                request=request,
            )

        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    result = _run(
        server._probe_website(
            "https://public.example.com"
        )
    )

    assert result["outcome"] == "reachable"
    assert result["url"] == (
        "https://www.public.example.com/site"
    )
    assert [
        request.headers["Host"]
        for request in requests
    ] == [
        "public.example.com",
        "www.public.example.com",
    ]
    assert all(
        request.url.host == "93.184.216.34"
        for request in requests
    )
    assert [
        request.extensions["sni_hostname"]
        for request in requests
    ] == [
        "public.example.com",
        "www.public.example.com",
    ]


def test_dns_rebinding_connects_to_validated_ip(monkeypatch):
    requests = []
    resolutions = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    client_options = _install_http_handler(
        monkeypatch,
        handler,
    )

    def rebinding_getaddrinfo(
        hostname,
        port,
        _family=0,
        _socket_type=0,
    ):
        resolutions.append(hostname)
        address = (
            "93.184.216.34"
            if len(resolutions) == 1
            else "127.0.0.1"
        )
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, port),
            )
        ]

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        rebinding_getaddrinfo,
    )

    result = _run(
        server._probe_website(
            "https://public.example.com/path"
        )
    )

    assert result["outcome"] == "reachable"
    assert result["url"] == (
        "https://public.example.com/path"
    )
    assert resolutions == ["public.example.com"]
    assert len(requests) == 1

    request = requests[0]
    assert request.url.host == "93.184.216.34"
    assert request.headers["Host"] == "public.example.com"
    assert request.extensions["sni_hostname"] == (
        "public.example.com"
    )
    assert client_options[0]["trust_env"] is False
    assert (
        client_options[0]["limits"].max_keepalive_connections
        == 0
    )


def test_ssrf_rejects_mixed_public_and_private_dns(
    monkeypatch,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    def mixed_getaddrinfo(
        _hostname,
        port,
        _family=0,
        _socket_type=0,
    ):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            ),
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("10.0.0.10", port),
            ),
        ]

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        mixed_getaddrinfo,
    )

    result = _run(
        server._probe_website(
            "https://public.example.com"
        )
    )

    assert result["outcome"] == "unsafe"
    assert requests == []


def test_global_ipv6_is_bracketed_in_connection_url(
    monkeypatch,
):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    def ipv6_getaddrinfo(
        _hostname,
        port,
        _family=0,
        _socket_type=0,
    ):
        return [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2606:4700:4700::1111", port, 0, 0),
            )
        ]

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        ipv6_getaddrinfo,
    )

    result = _run(
        server._probe_website(
            "https://public.example.com/ipv6"
        )
    )

    assert result["outcome"] == "reachable"
    assert len(requests) == 1
    assert requests[0].url.host == (
        "2606:4700:4700::1111"
    )
    assert "[2606:4700:4700::1111]" in str(
        requests[0].url
    )
    assert requests[0].headers["Host"] == (
        "public.example.com"
    )


def test_redirect_revalidates_dns_before_second_request(
    monkeypatch,
):
    requests = []
    resolutions = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            302,
            headers={"Location": "/private"},
            request=request,
        )

    _install_http_handler(monkeypatch, handler)

    def changing_getaddrinfo(
        hostname,
        port,
        _family=0,
        _socket_type=0,
    ):
        resolutions.append(hostname)
        address = (
            "93.184.216.34"
            if len(resolutions) == 1
            else "127.0.0.1"
        )
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, port),
            )
        ]

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        changing_getaddrinfo,
    )

    result = _run(
        server._probe_website(
            "https://public.example.com/start"
        )
    )

    assert result["outcome"] == "unsafe"
    assert resolutions == [
        "public.example.com",
        "public.example.com",
    ]
    assert len(requests) == 1
    assert requests[0].url.host == "93.184.216.34"


def test_dns_failure_is_unknown(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return _ok_handler(request)

    _install_http_handler(monkeypatch, handler)

    def failed_getaddrinfo(*_args):
        raise socket.gaierror("DNS indisponível")

    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        failed_getaddrinfo,
    )

    result = _run(
        server._probe_website(
            "https://public.example.com"
        )
    )

    assert result["outcome"] == "unknown"
    assert requests == []


@pytest.mark.parametrize(
    ("business_name", "result"),
    [
        (
            "Clínica Exemplo",
            {
                "url": "https://outraclinica.com.br",
                "title": (
                    "Clínica odontológica em Belo Horizonte"
                ),
            },
        ),
        (
            "Restaurante Sabor Real",
            {
                "url": "https://restaurantequalquer.com.br",
                "title": "Restaurante em Belo Horizonte",
            },
        ),
        (
            "Studio Bella",
            {
                "url": "https://empresaerrada.com.br",
                "title": "Studio de beleza em BH",
            },
        ),
    ],
)
def test_search_identity_rejects_generic_matches(
    business_name,
    result,
):
    assert not server._is_reliable_search_result(
        result,
        business_name,
    )


@pytest.mark.parametrize(
    ("business_name", "result"),
    [
        (
            "Clínica OdontoMais",
            {
                "url": "https://odontomais.com.br",
                "title": "Clínica OdontoMais — Site oficial",
            },
        ),
        (
            "Restaurante Sabor Real",
            {
                "url": "https://saboreal.com.br",
                "title": "Restaurante Sabor Real",
            },
        ),
        (
            "Studio Bella",
            {
                "url": "https://studiobella.com.br",
                "title": "Studio Bella",
            },
        ),
    ],
)
def test_search_identity_accepts_strong_matches(
    business_name,
    result,
):
    assert server._is_reliable_search_result(
        result,
        business_name,
    )


def test_brave_search_uses_brazilian_localization(
    monkeypatch,
):
    captured_requests = []

    def handler(request):
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={"web": {"results": []}},
            request=request,
        )

    _install_http_handler(monkeypatch, handler)
    monkeypatch.setattr(
        server,
        "WEBSITE_DISCOVERY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        server,
        "BRAVE_SEARCH_API_KEY",
        "secret-test-key",
    )

    result = _run(
        server.search_web_for_website(
            "Clínica OdontoMais",
            "Belo Horizonte, MG",
        )
    )

    assert result == []
    assert len(captured_requests) == 1

    request = captured_requests[0]
    assert request.method == "GET"
    assert str(request.url.copy_with(query=None)) == (
        server.BRAVE_SEARCH_URL
    )
    assert request.headers["X-Subscription-Token"] == (
        "secret-test-key"
    )
    assert request.url.params["country"] == "BR"
    assert request.url.params["search_lang"] == "pt"
    assert request.url.params["ui_lang"] == "pt-BR"
    assert request.url.params["count"] == "5"
    assert "Clínica OdontoMais" in request.url.params["q"]
    assert "Belo Horizonte, MG" in request.url.params["q"]
