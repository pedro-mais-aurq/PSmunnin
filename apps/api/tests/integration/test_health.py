
from httpx import AsyncClient
from leadhunter_api.main import app


async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert data["database"] in ["ok", "error"]
        assert data["redis"] in ["ok", "error"]
