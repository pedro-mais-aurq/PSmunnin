
import httpx


class SharedHTTPClient:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self._client

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
