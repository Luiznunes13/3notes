import pytest
import httpx
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    from app.main import app
    from app.database import create_db_and_tables
    create_db_and_tables()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model" in data


@pytest.mark.anyio
async def test_criar_equipamento(client):
    resp = await client.post("/api/equipamentos", json={
        "patrimonio": "TEST-999",
        "descricao": "Equipamento de teste",
        "tipo": "Teste",
        "setor": "Lab",
        "localizacao": "Lab-1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["patrimonio"] == "TEST-999"
    assert data["id"] is not None


@pytest.mark.anyio
@pytest.mark.requires_ollama
async def test_chat_basico(client):
    resp = await client.post("/ai/chat", json={
        "mensagem": "Olá, quero reportar um problema.",
        "historico": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["resposta"], str)
    assert len(data["resposta"]) > 0


@pytest.mark.anyio
@pytest.mark.requires_ollama
async def test_fluxo_chamado(client):
    resp1 = await client.post("/ai/chat", json={
        "mensagem": "[Setor: UTI] A bomba de infusão VM-001 está com alarme e não infunde.",
        "historico": [],
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["resposta"]

    historico = [
        {"role": "user", "content": "[Setor: UTI] A bomba de infusão VM-001 está com alarme e não infunde."},
        {"role": "assistant", "content": data1["resposta"]},
    ]

    resp2 = await client.post("/ai/chat", json={
        "mensagem": "Sou Maria Silva, da UTI. Patrimônio VM-001, setor UTI.",
        "historico": historico,
    })
    assert resp2.status_code == 200
