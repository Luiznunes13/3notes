from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import AgendaPreventiva, AgendaPreventivaRead

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("", response_model=list[AgendaPreventivaRead])
def listar_agenda(mes: Optional[str] = None, session: Session = Depends(get_session)):
    query = select(AgendaPreventiva)
    if mes:
        try:
            ano, m = mes.split("-")
            inicio = date(int(ano), int(m), 1)
            if int(m) == 12:
                fim = date(int(ano) + 1, 1, 1)
            else:
                fim = date(int(ano), int(m) + 1, 1)
            query = query.where(AgendaPreventiva.data_programada >= inicio).where(
                AgendaPreventiva.data_programada < fim
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="Formato de mês inválido. Use YYYY-MM")
    return session.exec(query).all()


@router.post("/{id}/executar", response_model=AgendaPreventivaRead)
def executar_agenda(id: int, body: dict, session: Session = Depends(get_session)):
    agenda = session.get(AgendaPreventiva, id)
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda não encontrada")
    agenda.data_executada = date.today()
    agenda.status = "executado"
    agenda.tecnico = body.get("tecnico")
    if body.get("observacoes"):
        import json
        existing = json.loads(agenda.checklist_json) if agenda.checklist_json else {}
        existing["observacoes"] = body["observacoes"]
        agenda.checklist_json = json.dumps(existing, ensure_ascii=False)
    session.add(agenda)
    session.commit()
    session.refresh(agenda)
    return agenda
