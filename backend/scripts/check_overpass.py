"""Optional real connectivity check. Run manually: python -m scripts.check_overpass."""
import argparse
import asyncio
import time

import httpx
from overpass_config import OVERPASS_ENDPOINTS, OVERPASS_TIMEOUT, USER_AGENT

# Lookup at most one OSM element; no region search and no database access.
DIAGNOSTIC_QUERY = "[out:json][timeout:5];node(1);out ids;"


async def probe_endpoint(client: httpx.AsyncClient, endpoint: str) -> dict[str, str | float]:
    started = time.perf_counter()
    status = "transport_error"
    result = "failed"
    try:
        response = await client.post(
            endpoint,
            data={"data": DIAGNOSTIC_QUERY},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        status = str(response.status_code)
        if response.is_success:
            try:
                data = response.json()
                valid = (
                    isinstance(data, dict)
                    and isinstance(data.get("elements"), list)
                    and all(isinstance(element, dict) for element in data["elements"])
                    and not data.get("remark")
                )
            except ValueError:
                valid = False
            result = "ok" if valid else "invalid_response"
    except httpx.TimeoutException:
        status = "timeout"
    except httpx.ConnectError:
        status = "connect_error"
    except httpx.TransportError:
        status = "transport_error"
    except httpx.DecodingError:
        status = "invalid_response"

    return {
        "endpoint": endpoint,
        "status": status,
        "result": result,
        "elapsed": time.perf_counter() - started,
    }


async def check_endpoints() -> int:
    failed = False
    async with httpx.AsyncClient(timeout=OVERPASS_TIMEOUT) as client:
        for endpoint in OVERPASS_ENDPOINTS:
            print(f"{endpoint}\nchecking...", flush=True)
            result = await probe_endpoint(client, endpoint)
            print(
                f"status={result['status']} result={result['result']} "
                f"elapsed={result['elapsed']:.1f}s\n",
                flush=True,
            )
            failed |= result["result"] != "ok"
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Testa cada endpoint Overpass uma vez, com uma query mínima real. "
            "Usa OVERPASS_ENDPOINTS, OSM_USER_AGENT e os timeouts da aplicação. "
            "Não acessa o banco. Execute somente sob demanda, nunca no CI."
        ),
        epilog="Saída: 0 se todos responderem com dados válidos; 1 se qualquer um falhar.",
    )
    parser.parse_args()
    return asyncio.run(check_endpoints())


if __name__ == "__main__":
    raise SystemExit(main())
