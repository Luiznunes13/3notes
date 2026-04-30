from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import Chamado, ChamadoCreate, ChamadoEdit, ChamadoRead, HistoricoStatus, HistoricoStatusRead

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


@router.patch("/{id}/editar", response_model=ChamadoRead)
def editar_chamado(id: int, data: ChamadoEdit, session: Session = Depends(get_session)):
    """Master edita campos do chamado antes de validar. Atualiza o .md em disco."""
    chamado = session.get(Chamado, id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    campos = data.model_dump(exclude_unset=True, exclude={"tags_finais"})
    for campo, valor in campos.items():
        setattr(chamado, campo, valor)

    # Re-gera o .md com os dados corrigidos (se existir)
    if chamado.md_path:
        try:
            import json as _json
            from app.services.markdown_service import markdown_service
            from app.models import Equipamento as EqModel

            eq = session.get(EqModel, chamado.equipamento_id)
            patrimonio = eq.patrimonio if eq else "N/A"
            setor = eq.setor if eq else chamado.setor_reportador

            tags = data.tags_finais or []
            if not tags:
                # Tenta extrair tags do .md atual
                import re as _re
                conteudo_atual = markdown_service.ler_md(chamado.md_path)
                m = _re.search(r'^tags: (\[.*?\])', conteudo_atual, _re.MULTILINE)
                if m:
                    try:
                        tags = _json.loads(m.group(1))
                    except Exception:
                        tags = []

            ano = chamado.criado_em.year
            chm_id = f"CHM-{ano}-{chamado.id:04d}"
            titulo = f"{chm_id} {eq.descricao if eq else 'Equipamento'} — Problema reportado"

            dados_md = {
                "chamado_id": chm_id,
                "patrimonio": patrimonio,
                "setor": setor,
                "setor_reportador": chamado.setor_reportador,
                "aberto_por": chamado.aberto_por,
                "descricao_problema": chamado.descricao,
                "criticidade_sugerida": chamado.criticidade_sugerida or "medio",
            }
            conteudo = markdown_service.gerar_md_chamado(dados_md, titulo, tags, [])
            markdown_service.salvar_md(
                conteudo,
                "chamados",
                f"CHM-{ano}-{chamado.id:04d}",
            )
        except Exception:
            pass

    session.add(chamado)
    session.commit()
    session.refresh(chamado)
    return chamado


@router.patch("/{id}/validar", response_model=ChamadoRead)
async def validar_chamado(id: int, body: dict, session: Session = Depends(get_session)):
    """Master aprova o chamado: marca validado=True e dispara o embedding no ChromaDB."""
    chamado = session.get(Chamado, id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    if chamado.validado:
        raise HTTPException(status_code=409, detail="Chamado já foi validado")

    validado_por = body.get("validado_por", "master")
    chamado.validado = True
    chamado.validado_por = validado_por
    chamado.validado_em = datetime.utcnow()
    session.add(chamado)
    session.commit()
    session.refresh(chamado)

    # Dispara embedding agora que o dado foi aprovado
    if chamado.md_path:
        try:
            import json as _json
            from app.services.rag_service import rag_service
            from app.models import FonteConhecimento, Equipamento as EqModel

            eq = session.get(EqModel, chamado.equipamento_id)
            ano = chamado.criado_em.year
            chm_id = f"CHM-{ano}-{chamado.id:04d}"
            titulo = f"{chm_id} {eq.descricao if eq else chamado.descricao[:50]}"

            metadata = {
                "titulo": titulo,
                "tipo": "chamado_aberto",
                "patrimonio": eq.patrimonio if eq else "N/A",
                "setor": chamado.setor_reportador,
                "arquivo_path": chamado.md_path,
            }
            await rag_service.indexar_documento(chamado.md_path, metadata)

            # Registra na tabela FonteConhecimento
            fonte_existente = session.exec(
                select(FonteConhecimento).where(FonteConhecimento.arquivo_path == chamado.md_path)
            ).first()
            if not fonte_existente:
                fonte = FonteConhecimento(
                    titulo=titulo,
                    tipo="chamado_aberto",
                    arquivo_path=chamado.md_path,
                    tags="[]",
                )
                session.add(fonte)
                session.commit()
        except Exception:
            pass  # Embedding é não-fatal

    return chamado


@router.get("/{id}/md")
def conteudo_md(id: int, session: Session = Depends(get_session)):
    """Return the raw .md content for a chamado so the dashboard can render it."""
    chamado = session.get(Chamado, id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    if not chamado.md_path:
        raise HTTPException(status_code=404, detail="Chamado sem nota .md")
    from app.services.markdown_service import markdown_service
    conteudo = markdown_service.ler_md(chamado.md_path)
    if not conteudo:
        raise HTTPException(status_code=404, detail="Arquivo .md não encontrado em disco")
    return {"md_path": chamado.md_path, "conteudo": conteudo}


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
                    import re as _re
                    from app.services.markdown_service import markdown_service
                    from app.services.rag_service import rag_service
                    import asyncio

                    loop = asyncio.new_event_loop()

                    # Find related chamados via RAG (Obsidian-style cluster)
                    relacionados: list[str] = []
                    try:
                        self_id = markdown_service.parse_frontmatter(chamado.md_path).get("id", "")
                        query = f"{chamado.descricao}\n{body['resolucao']}"
                        snippets = loop.run_until_complete(
                            rag_service.buscar_contexto(query, n_resultados=4)
                        )
                        ids_vistos: set[str] = set()
                        for sn in snippets:
                            for m in _re.findall(r"CHM-\d{4}-\d{4}", sn):
                                if m != self_id and m not in ids_vistos:
                                    ids_vistos.add(m)
                                    relacionados.append(m)
                                    if len(relacionados) >= 3:
                                        break
                            if len(relacionados) >= 3:
                                break
                    except Exception:
                        relacionados = []

                    markdown_service.atualizar_md_resolucao(
                        chamado.md_path, body["resolucao"], alterado_por, relacionados
                    )
                    # Re-index updated .md as chamado_resolvido
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
