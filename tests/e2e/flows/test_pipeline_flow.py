
"""
E2E: Fluxo completo de pipeline
"""
import pytest


@pytest.mark.e2e
async def test_full_pipeline_flow():
    """
    1. Criar pipeline run
    2. Aguardar processamento
    3. Verificar leads criados
    4. Verificar scores calculados
    5. Verificar análises persistidas
    """
    pass  # Implementar com testcontainers
