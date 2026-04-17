"""
Knowledge Base router — upload, indexing, semantic search.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.database import get_session
from app.models import FonteConhecimento

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "./knowledge")


def _extrair_texto_pdf(conteudo_bytes: bytes) -> str:
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(conteudo_bytes)) as pdf:
            partes = []
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    partes.append(texto)
            return "\n\n".join(partes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Erro ao extrair texto do PDF: {str(e)}")


@router.post("/upload", status_code=201)
async def upload_fonte(
    file: UploadFile = File(...),
    tipo: str = Form(default="documento"),
    tags: str = Form(default="[]"),
    session: Session = Depends(get_session),
):
    """Upload a .md, .txt or .pdf and index it in ChromaDB."""
    from app.services.rag_service import rag_service

    conteudo_bytes = await file.read()
    nome_arquivo = file.filename or "documento"
    ext = Path(nome_arquivo).suffix.lower()

    if ext == ".pdf":
        conteudo_texto = _extrair_texto_pdf(conteudo_bytes)
        nome_md = nome_arquivo.replace(".pdf", ".md")
    elif ext in (".md", ".txt"):
        conteudo_texto = conteudo_bytes.decode("utf-8", errors="replace")
        nome_md = nome_arquivo if ext == ".md" else nome_arquivo.replace(".txt", ".md")
    else:
        raise HTTPException(status_code=422, detail="Formato não suportado. Use .md, .txt ou .pdf.")

    # Parse tags
    try:
        tags_list = json.loads(tags) if tags else []
    except Exception:
        tags_list = []

    # Save file to knowledge/{tipo}/
    subpasta = tipo
    pasta = Path(KNOWLEDGE_DIR) / subpasta
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome_md
    caminho.write_text(conteudo_texto, encoding="utf-8")
    arquivo_path = str(caminho)

    titulo = Path(nome_md).stem.replace("-", " ").replace("_", " ").title()

    # Index in ChromaDB
    metadata = {
        "titulo": titulo,
        "tipo": tipo,
        "tags": json.dumps(tags_list, ensure_ascii=False),
        "arquivo_path": arquivo_path,
    }
    try:
        await rag_service.indexar_documento(arquivo_path, metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao indexar no ChromaDB: {str(e)}")

    # Register in SQL
    fonte = FonteConhecimento(
        titulo=titulo,
        tipo=tipo,
        arquivo_path=arquivo_path,
        tags=json.dumps(tags_list, ensure_ascii=False),
        indexado_em=datetime.utcnow(),
        ativo=True,
    )
    session.add(fonte)
    session.commit()
    session.refresh(fonte)

    return {
        "id": fonte.id,
        "titulo": fonte.titulo,
        "tipo": fonte.tipo,
        "tags": tags_list,
        "indexado_em": fonte.indexado_em,
        "arquivo_path": arquivo_path,
    }


@router.get("/fontes")
def listar_fontes(session: Session = Depends(get_session)):
    """List all active knowledge sources."""
    fontes = session.exec(
        select(FonteConhecimento).where(FonteConhecimento.ativo == True)
    ).all()
    result = []
    for f in fontes:
        try:
            tags_list = json.loads(f.tags) if f.tags else []
        except Exception:
            tags_list = []
        result.append({
            "id": f.id,
            "titulo": f.titulo,
            "tipo": f.tipo,
            "arquivo_path": f.arquivo_path,
            "tags": tags_list,
            "indexado_em": f.indexado_em,
            "ativo": f.ativo,
        })
    return result


@router.get("/buscar")
async def buscar_conhecimento(q: str):
    """Semantic search in ChromaDB. Returns top 5 relevant chunks."""
    from app.services.rag_service import rag_service

    if not q or len(q.strip()) < 3:
        raise HTTPException(status_code=422, detail="Query muito curta.")

    snippets = await rag_service.buscar_contexto(q, n_resultados=5)
    resultados = []
    for snippet in snippets:
        partes = snippet.split("\n", 1)
        fonte = partes[0].strip("()") if partes[0].startswith("(") else "desconhecido"
        trecho = partes[1].strip() if len(partes) > 1 else snippet
        resultados.append({"fonte": fonte, "trecho": trecho})
    return resultados


@router.delete("/fontes/{fonte_id}", status_code=204)
def remover_fonte(fonte_id: int, session: Session = Depends(get_session)):
    """Deactivate a knowledge source (removes from ChromaDB, marks SQL as inactive)."""
    from app.services.rag_service import rag_service

    fonte = session.get(FonteConhecimento, fonte_id)
    if not fonte:
        raise HTTPException(status_code=404, detail="Fonte não encontrada.")

    rag_service.remover_documento(fonte.arquivo_path)
    fonte.ativo = False
    session.add(fonte)
    session.commit()
