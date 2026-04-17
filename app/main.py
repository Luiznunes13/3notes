import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.routers import equipamentos, chamados, agenda, ai, knowledge
from app.models import Equipamento

load_dotenv()

THREENNOTES_MODEL = os.getenv("THREENNOTES_MODEL", "gemma4:27b")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    # generate preventive schedule on startup
    from app.services.agenda_service import gerar_agenda_pendente
    with Session(engine) as session:
        gerar_agenda_pendente(session)

    yield


app = FastAPI(title="3Notes.AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(equipamentos.router, prefix="/api")
app.include_router(chamados.router, prefix="/api")
app.include_router(agenda.router, prefix="/api")
app.include_router(ai.router)
app.include_router(knowledge.router, prefix="/api")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/static/reporter.html")


@app.get("/health")
def health():
    return {"status": "ok", "model": THREENNOTES_MODEL}


@app.get("/api/metricas")
def metricas():
    from datetime import datetime, timezone
    from sqlmodel import Session, func
    from app.models import Chamado, FonteConhecimento

    with Session(engine) as session:
        todos = session.exec(select(Chamado)).all()
        fontes_count = len(session.exec(
            select(FonteConhecimento).where(FonteConhecimento.ativo == True)
        ).all())

    abertos = [c for c in todos if c.status not in ("resolvido", "cancelado")]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    mes_atual = now.month
    ano_atual = now.year
    do_mes = [c for c in todos if c.criado_em.month == mes_atual and c.criado_em.year == ano_atual]

    resolvidos_com_sla = [
        c for c in todos if c.fechado_em and c.criado_em
    ]
    if resolvidos_com_sla:
        sla_medio = sum(
            (c.fechado_em - c.criado_em).total_seconds() / 3600 for c in resolvidos_com_sla
        ) / len(resolvidos_com_sla)
    else:
        sla_medio = 0

    por_setor: dict[str, int] = {}
    for c in todos:
        por_setor[c.setor_reportador] = por_setor.get(c.setor_reportador, 0) + 1
    por_setor_list = sorted(
        [{"setor": k, "total": v} for k, v in por_setor.items()],
        key=lambda x: -x["total"],
    )[:5]

    por_criticidade: dict[str, int] = {}
    for c in todos:
        nivel = c.criticidade_confirmada or c.criticidade_sugerida or "desconhecido"
        por_criticidade[nivel] = por_criticidade.get(nivel, 0) + 1
    por_criticidade_list = [{"nivel": k, "total": v} for k, v in por_criticidade.items()]

    eq_count: dict[int, int] = {}
    for c in todos:
        eq_count[c.equipamento_id] = eq_count.get(c.equipamento_id, 0) + 1

    with Session(engine) as session:
        top_eqs = []
        for eq_id, count in sorted(eq_count.items(), key=lambda x: -x[1])[:5]:
            eq = session.get(Equipamento, eq_id)
            if eq:
                top_eqs.append({"patrimonio": eq.patrimonio, "descricao": eq.descricao, "total_chamados": count})

    return {
        "chamados_abertos": len(abertos),
        "chamados_mes": len(do_mes),
        "sla_medio_horas": round(sla_medio, 1),
        "por_setor": por_setor_list,
        "por_criticidade": por_criticidade_list,
        "top_equipamentos": top_eqs,
        "fontes_conhecimento": fontes_count,
    }
