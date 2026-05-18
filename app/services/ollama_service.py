import os
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

SYSTEM_PROMPT_COPILOT = """Você é o copiloto de manutenção hospitalar do 3Notes.AI.

FUNÇÃO: Responder dúvidas sobre equipamentos médicos, sugerir criticidade e citar casos resolvidos da base de conhecimento.

REGRAS:
- Seja CONCISO. Máximo 3 parágrafos curtos.
- Nunca conduza um fluxo de perguntas — apenas responda o que foi perguntado.
- Se não encontrar nada relevante na base, diga explicitamente: "Não encontrei casos similares na base de conhecimento."

CITAÇÃO OBRIGATÓRIA — siga este formato rigorosamente:
- Sempre que usar informação do CONTEXTO RELEVANTE, cite a fonte entre colchetes imediatamente após a informação.
- Para chamados resolvidos: use o ID exato entre colchetes, ex: [CHM-2026-0021]
- Para documentos (manuais, protocolos): use o título entre colchetes, ex: [Boas Práticas — Dashboard]
- Nunca afirme algo técnico sem citar a fonte.
- Exemplo correto: "O alarme E05 indica obstrução do sensor de oclusão [CHM-2026-0003]. A solução foi limpeza com solução enzimática e recalibração em 150 mmHg."

CRITICIDADE:
- crítico: equipamento em uso direto com paciente, sem substituto disponível
- alto: equipamento importante, substituto disponível
- médio: equipamento de suporte, substituto disponível
- baixo: equipamento auxiliar, baixo impacto clínico imediato"""

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
        _, payload = await self._build_chat_payload(messages, system_prompt, stream=False)
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Serviço de IA indisponível. Verifique se o Ollama está rodando.")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Erro ao comunicar com o modelo: {type(e).__name__}: {str(e)}")

    async def _build_chat_payload(
        self, messages: list[dict], system_prompt: str | None = None, stream: bool = False
    ) -> tuple[str, dict]:
        if system_prompt is None:
            system_prompt = SYSTEM_PROMPT_INTAKE
        """Build Ollama payload with RAG context injected. Returns (model, payload)."""
        rag_context = ""
        try:
            from app.services.rag_service import rag_service
            user_messages = [m for m in messages if m["role"] == "user"]
            if user_messages:
                last_user_msg = user_messages[-1]["content"]
                contextos = await rag_service.buscar_contexto(last_user_msg, n_resultados=3)
                if contextos:
                    rag_context = (
                        "CONTEXTO RELEVANTE (base de conhecimento do hospital):\n"
                        "─────────────────────────────────────────────────────\n"
                        + "\n".join(f"[Fonte {i+1}] {c}" for i, c in enumerate(contextos))
                        + "\n─────────────────────────────────────────────────────\n\n"
                    )
        except Exception:
            pass

        full_system = rag_context + system_prompt
        model = await self._get_active_model()
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": full_system}] + messages,
            "stream": stream,
        }
        return model, payload

    async def chat_stream(self, messages: list[dict], system_prompt: str | None = None):
        """Streaming chat — yields text chunks as they arrive from Ollama."""
        import json as _json
        _, payload = await self._build_chat_payload(messages, system_prompt, stream=True)
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = _json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except _json.JSONDecodeError:
                            continue
        except Exception:
            return

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
        """Gera embedding via Ollama embed API. Trunca para EMBED_DIMS (Matryoshka)."""
        from app.services.rag_service import EMBED_DIMS
        embed_model = os.getenv("THREENNOTES_EMBED_MODEL", "qwen3-embedding:0.6b")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": embed_model, "input": texto},
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    vec = embeddings[0]
                    return vec[:EMBED_DIMS] if len(vec) > EMBED_DIMS else vec
        except Exception:
            pass
        return []


ollama_service = OllamaService()
