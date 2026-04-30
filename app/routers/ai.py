import json
import re
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import Chamado, Equipamento, FonteConhecimento
from app.services.ollama_service import ollama_service

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    mensagem: str
    historico: list[dict] = []
    modo: str = "intake"  # "intake" | "copiloto"


class ConfirmarChamadoRequest(BaseModel):
    equipamento_descricao: str
    patrimonio: str
    setor: str
    setor_reportador: str
    aberto_por: str
    descricao_problema: str
    criticidade_sugerida: str
    justificativa: Optional[str] = None
    conversa_json: Optional[str] = None
    titulo_final: Optional[str] = None
    tags_finais: list[str] = []


class SugerirTituloRequest(BaseModel):
    equipamento_descricao: str
    descricao_problema: str


class SugerirTagsRequest(BaseModel):
    equipamento_descricao: str
    descricao_problema: str
    setor: str = ""


class PreviewMdRequest(BaseModel):
    equipamento_descricao: str
    patrimonio: str
    setor: str
    setor_reportador: str
    aberto_por: str
    descricao_problema: str
    criticidade_sugerida: str
    titulo: str
    tags: list[str] = []
    conversa_json: Optional[str] = None


def _extract_action(text: str) -> tuple[Optional[str], Optional[dict]]:
    match = re.search(r'\{.*"action"\s*:\s*"criar_chamado".*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return data.get("action"), data.get("dados")
        except json.JSONDecodeError:
            pass
    return None, None


def _get_system_prompt(modo: str):
    from app.services.ollama_service import SYSTEM_PROMPT_COPILOT, SYSTEM_PROMPT_INTAKE
    return SYSTEM_PROMPT_COPILOT if modo == "copiloto" else SYSTEM_PROMPT_INTAKE


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = list(req.historico)
    messages.append({"role": "user", "content": req.mensagem})
    resposta = await ollama_service.chat(messages, system_prompt=_get_system_prompt(req.modo))
    action, dados = _extract_action(resposta)
    return {"resposta": resposta, "action": action, "dados": dados}


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Streaming chat endpoint — returns text/event-stream with SSE chunks."""
    messages = list(req.historico)
    messages.append({"role": "user", "content": req.mensagem})
    system_prompt = _get_system_prompt(req.modo)
    full_response = []

    async def generate() -> AsyncGenerator[str, None]:
        async for token in ollama_service.chat_stream(messages, system_prompt=system_prompt):
            full_response.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        complete = "".join(full_response)
        action, dados = _extract_action(complete)
        yield f"data: {json.dumps({'done': True, 'action': action, 'dados': dados})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/sugerir-titulo")
async def sugerir_titulo(req: SugerirTituloRequest):
    """Generate a concise title for the .md."""
    prompt = (
        f"Gere um título conciso (máximo 8 palavras) para um chamado de manutenção hospitalar.\n"
        f"Equipamento: {req.equipamento_descricao}\n"
        f"Problema: {req.descricao_problema}\n"
        f"Formato: '{req.equipamento_descricao} — <problema em até 5 palavras>'\n"
        f"Responda APENAS com o título, sem aspas, sem explicações."
    )
    try:
        resposta = await ollama_service.completar(prompt)
        titulo = resposta.strip().strip('"').strip("'").split("\n")[0]
        if not titulo:
            titulo = f"{req.equipamento_descricao} — Problema reportado"
    except Exception:
        titulo = f"{req.equipamento_descricao} — Problema reportado"
    return {"titulo": titulo}


@router.post("/sugerir-tags")
async def sugerir_tags(req: SugerirTagsRequest):
    """Suggest kebab-case tags for the chamado."""
    from app.services.markdown_service import markdown_service

    texto = f"Equipamento: {req.equipamento_descricao}\nProblema: {req.descricao_problema}\nSetor: {req.setor}"
    tags = await markdown_service.sugerir_tags(texto)
    return {"tags": tags}


@router.post("/preview-md")
async def preview_md(req: PreviewMdRequest):
    """Generate the .md preview string (not saved to disk)."""
    from app.services.markdown_service import markdown_service

    conversa = []
    if req.conversa_json:
        try:
            conversa = json.loads(req.conversa_json)
        except Exception:
            conversa = []

    dados = {
        "chamado_id": "CHM-????",
        "patrimonio": req.patrimonio,
        "setor": req.setor,
        "setor_reportador": req.setor_reportador,
        "aberto_por": req.aberto_por,
        "descricao_problema": req.descricao_problema,
        "criticidade_sugerida": req.criticidade_sugerida,
    }
    conteudo = markdown_service.gerar_md_chamado(dados, req.titulo, req.tags, conversa)
    return {"conteudo_md": conteudo}


@router.post("/confirmar-chamado", status_code=201)
async def confirmar_chamado(
    req: ConfirmarChamadoRequest, session: Session = Depends(get_session)
):
    from app.services.markdown_service import markdown_service
    from app.services.rag_service import rag_service

    # 1. Ensure equipamento exists
    equipamento = session.exec(
        select(Equipamento).where(Equipamento.patrimonio == req.patrimonio)
    ).first()

    if not equipamento:
        equipamento = Equipamento(
            patrimonio=req.patrimonio,
            descricao=req.equipamento_descricao,
            tipo="Não especificado",
            setor=req.setor,
            localizacao=req.setor,
            criticidade_base=req.criticidade_sugerida,
        )
        session.add(equipamento)
        session.commit()
        session.refresh(equipamento)

    # 2. Create chamado (need id for .md filename)
    conversa = []
    if req.conversa_json:
        try:
            conversa = json.loads(req.conversa_json)
        except Exception:
            conversa = []

    chamado = Chamado(
        equipamento_id=equipamento.id,
        tipo="corretivo",
        aberto_por=req.aberto_por,
        setor_reportador=req.setor_reportador,
        descricao=req.descricao_problema,
        criticidade_sugerida=req.criticidade_sugerida,
        conversa_json=req.conversa_json,
    )
    session.add(chamado)
    session.commit()
    session.refresh(chamado)

    # 3. Generate and save .md
    ano = chamado.criado_em.year
    titulo_base = req.titulo_final or f"{req.equipamento_descricao} — Problema reportado"
    # Strip any placeholder CHM-YYYY-NNNN prefix coming from the frontend
    titulo_base = re.sub(r"^CHM-\d{4}-\d+\s*", "", titulo_base).strip()
    if not titulo_base:
        titulo_base = f"{req.equipamento_descricao} — Problema reportado"
    titulo_com_id = f"CHM-{ano}-{chamado.id:04d} {titulo_base}"

    dados_md = {
        "chamado_id": f"CHM-{ano}-{chamado.id:04d}",
        "patrimonio": req.patrimonio,
        "setor": req.setor,
        "setor_reportador": req.setor_reportador,
        "aberto_por": req.aberto_por,
        "descricao_problema": req.descricao_problema,
        "criticidade_sugerida": req.criticidade_sugerida,
    }
    conteudo_md = markdown_service.gerar_md_chamado(
        dados_md, titulo_com_id, req.tags_finais, conversa
    )
    nome_arquivo = f"CHM-{ano}-{chamado.id:04d}"
    md_path = markdown_service.salvar_md(conteudo_md, "chamados", nome_arquivo)

    # 4. Update chamado with md_path (validado=False — aguarda aprovação do master)
    chamado.md_path = md_path
    chamado.validado = False
    session.add(chamado)
    session.commit()

    # 5. ChromaDB embedding é DIFERIDO — acontece apenas após validação pelo master
    # O .md já está salvo em disco; o master pode editar antes de indexar.

    return {
        "id": chamado.id,
        "status": chamado.status,
        "criado_em": chamado.criado_em,
        "md_path": md_path,
        "validado": False,
    }
