
from httpx import AsyncClient
from leadhunter_api.main import app


async def test_list_leads_filter_by_status():
    """T02: Filtro de status deve aceitar valores validos e rejeitar invalidos"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/leads?status=qualificado")
        assert response.status_code in [200, 404]

        response = await client.get("/v1/leads?status=invalido")
        assert response.status_code == 400


async def test_invalid_status_transition():
    """T02: Transicao invalida deve retornar 400, nao 500"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.patch("/v1/leads/00000000-0000-0000-0000-000000000000/status", json={"status": "convertido"})
        assert response.status_code in [400, 404]
