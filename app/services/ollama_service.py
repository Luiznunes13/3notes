import os
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

SYSTEM_PROMPT_INTAKE = """Você é o assistente de manutenção do 3Notes.AI, sistema interno de um hospital.
Seu trabalho é coletar informações sobre um problema em equipamento médico para abrir um chamado de manutenção.

REGRAS:
- Faça exatamente UMA pergunta por vez.
- Nunca invente ou suponha o número de patrimônio — sempre pergunte se não foi informado.
- Nunca diga que vai "criar" o chamado — apenas diga que vai "registrar" ou "abrir" o chamado.
- Seja direto e amigável, como um colega prestativo.

FLUXO OBRIGATÓRIO — siga nesta ordem:
Passo 1: Se ainda não souber o NOME de quem está reportando, pergunte o nome.
Passo 2: Se ainda não souber o NÚMERO DE PATRIMÔNIO do equipamento (ex: VM-001, AC-003), pergunte.
Passo 3: Com nome e patrimônio coletados, sugira uma criticidade e apresente o resumo completo do chamado.
Passo 4: Peça confirmação. Quando o usuário confirmar, gere o JSON.

OBSERVAÇÃO: O usuário pode informar o setor na primeira mensagem ("Estou reportando do setor X"). Use esse setor como setor_reportador e como setor do equipamento. Não pergunte o setor novamente.

RESUMO antes de confirmar deve conter:
- Nome e setor de quem reporta
- Equipamento (descrição + patrimônio) e setor
- Descrição do problema
- Criticidade sugerida com justificativa

Quando o usuário confirmar o resumo, responda SOMENTE com este JSON (sem texto antes ou depois):
{"action": "criar_chamado", "dados": {"equipamento_descricao": "...", "patrimonio": "...", "setor": "...", "setor_reportador": "...", "aberto_por": "...", "descricao_problema": "...", "criticidade_sugerida": "...", "justificativa": "..."}}

Níveis de criticidade:
- crítico: equipamento em uso direto com paciente, sem substituto disponível
- alto: equipamento importante, substituto disponível
- médio: equipamento de suporte, substituto disponível
- baixo: equipamento auxiliar, baixo impacto clínico imediato"""


class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("THREENNOTES_MODEL", "gemma4:27b")
        self.fallback_model = os.getenv("THREENNOTES_FALLBACK_MODEL", "gemma4:e4b")

    async def _get_active_model(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    if any(self.model in m for m in models):
                        return self.model
                    if any(self.fallback_model in m for m in models):
                        return self.fallback_model
        except httpx.ConnectError:
            pass
        return self.fallback_model

    async def chat(self, messages: list[dict], system_prompt: str = SYSTEM_PROMPT_INTAKE) -> str:
        # RAG: inject relevant context from knowledge base
        rag_context = ""
        try:
            from app.services.rag_service import rag_service
            user_messages = [m for m in messages if m["role"] == "user"]
            if user_messages:
                last_user_msg = user_messages[-1]["content"]
                contextos = await rag_service.buscar_contexto(last_user_msg)
                if contextos:
                    rag_context = (
                        "CONTEXTO RELEVANTE (base de conhecimento do hospital):\n"
                        "─────────────────────────────────────────────────────\n"
                        + "\n".join(f"[Fonte {i+1}] {c}" for i, c in enumerate(contextos))
                        + "\n─────────────────────────────────────────────────────\n\n"
                    )
        except Exception:
            pass  # RAG failure is non-fatal

        full_system = rag_context + system_prompt

        model = await self._get_active_model()
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": full_system}] + messages,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Serviço de IA indisponível. Verifique se o Ollama está rodando.")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Erro ao comunicar com o modelo: {str(e)}")

    async def completar(self, prompt: str) -> str:
        """Single-turn completion (sem histórico) para geração de metadados."""
        model = await self._get_active_model()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except Exception:
            return ""

    async def embed(self, texto: str) -> list[float]:
        """Gera embedding via Ollama embed API."""
        embed_model = os.getenv("THREENNOTES_EMBED_MODEL", "nomic-embed-text")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": embed_model, "input": texto},
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
        except Exception:
            pass
        return []


ollama_service = OllamaService()
