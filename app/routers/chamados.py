from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import Chamado, ChamadoCreate, ChamadoRead, HistoricoStatus, HistoricoStatusRead

router = APIRouter(prefix="/chamados", tags=["chamados"])

CRITICIDADE_ORDEM = {"critico": 0, "alto": 1, "medio": 2, "baixo": 3}


def _criticidade_sort(c: Chamado):
    nivel = c.criticidade_confirmada or c.criticidade_sugerida or "baixo"
    return (CRITICIDADE_ORDEM.get(nivel, 99), c.criado_em)


@router.post("", response_model=ChamadoRead, status_code=201)
def criar_chamado(data: ChamadoCreate, session: Session = Depends(get_session)):
    chamado = Chamado.model_validate(data)
    session.add(chamado)
    session.commit()
    session.refresh(chamado)
    return chamado


@router.get("", response_model=list[ChamadoRead])
def listar_chamados(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    equipamento_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    query = select(Chamado)
    if status:
        statuses = status.split(",")
        query = query.where(Chamado.status.in_(statuses))
    if tipo:
        query = query.where(Chamado.tipo == tipo)
    if equipamento_id:
        query = query.where(Chamado.equipamento_id == equipamento_id)
    results = session.exec(query).all()
    return sorted(results, key=_criticidade_sort)


@router.get("/{id}")
def detalhe_chamado(id: int, session: Session = Depends(get_session)):
    chamado = session.get(Chamado, id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    historico = session.exec(select(HistoricoStatus).where(HistoricoStatus.chamado_id == id)).all()
    return {
        **ChamadoRead.model_validate(chamado).model_dump(),
        "historico": [HistoricoStatusRead.model_validate(h).model_dump() for h in historico],
    }


@router.patch("/{id}/status")
def atualizar_status(
    id: int,
    body: dict,
    session: Session = Depends(get_session),
):
    chamado = session.get(Chamado, id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    novo_status = body.get("status")
    alterado_por = body.get("alterado_por", "sistema")
    observacao = body.get("observacao")

    if not novo_status:
        raise HTTPException(status_code=422, detail="Campo 'status' obrigatório")

    historico = HistoricoStatus(
        chamado_id=id,
        status_anterior=chamado.status,
        status_novo=novo_status,
        alterado_por=alterado_por,
        observacao=observacao,
    )
    session.add(historico)

    chamado.status = novo_status
    if novo_status == "resolvido":
        chamado.fechado_em = datetime.utcnow()
        if body.get("resolucao"):
            chamado.resolucao = body["resolucao"]
            # Update .md with resolution and re-index in ChromaDB
            if chamado.md_path:
                try:
                    from app.services.markdown_service import markdown_service
                    from app.services.rag_service import rag_service
                    import asyncio
                    markdown_service.atualizar_md_resolucao(
                        chamado.md_path, body["resolucao"], alterado_por
                    )
                    # Re-index updated .md (run async in sync context)
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(
                        rag_service.indexar_documento(chamado.md_path, {
                            "titulo": chamado.descricao[:80],
                            "tipo": "chamado_resolvido",
                            "arquivo_path": chamado.md_path,
                        })
                    )
                    loop.close()
                except Exception:
                    pass  # Non-fatal

    session.add(chamado)
    session.commit()
    session.refresh(chamado)
    return ChamadoRead.model_validate(chamado)


@router.patch("/{id}/criticidade", response_model=ChamadoRead)
def confirmar_criticidade(id: int, body: dict, session: Session = Depends(get_session)):
    chamado = session.get(Chamado, id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    criticidade = body.get("criticidade_confirmada")
    if not criticidade:
        raise HTTPException(status_code=422, detail="Campo 'criticidade_confirmada' obrigatório")
    chamado.criticidade_confirmada = criticidade
    session.add(chamado)
    session.commit()
    session.refresh(chamado)
    return chamado
