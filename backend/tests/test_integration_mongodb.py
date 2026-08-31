import asyncio
import importlib
import os

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


@pytest.mark.integration
def test_mongodb_connection_smoke():
    if os.getenv("RUN_MONGODB_INTEGRATION") != "1":
        pytest.skip(
            "Defina RUN_MONGODB_INTEGRATION=1 para testar o MongoDB."
        )

    result = asyncio.run(
        server.db.command("ping")
    )

    assert result["ok"] == 1.0
