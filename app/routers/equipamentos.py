from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import Equipamento, EquipamentoCreate, EquipamentoRead, EquipamentoUpdate

router = APIRouter(prefix="/equipamentos", tags=["equipamentos"])


@router.post("", response_model=EquipamentoRead, status_code=201)
def criar_equipamento(data: EquipamentoCreate, session: Session = Depends(get_session)):
    eq = Equipamento.model_validate(data)
    session.add(eq)
    session.commit()
    session.refresh(eq)
    return eq


@router.get("", response_model=list[EquipamentoRead])
def listar_equipamentos(ativo: Optional[bool] = None, session: Session = Depends(get_session)):
    query = select(Equipamento)
    if ativo is not None:
        query = query.where(Equipamento.ativo == ativo)
    return session.exec(query).all()


@router.get("/{id}", response_model=EquipamentoRead)
def detalhe_equipamento(id: int, session: Session = Depends(get_session)):
    eq = session.get(Equipamento, id)
    if not eq:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    return eq


@router.patch("/{id}", response_model=EquipamentoRead)
def atualizar_equipamento(id: int, data: EquipamentoUpdate, session: Session = Depends(get_session)):
    eq = session.get(Equipamento, id)
    if not eq:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(eq, field, value)
    session.add(eq)
    session.commit()
    session.refresh(eq)
    return eq


@router.delete("/{id}", status_code=204)
def deletar_equipamento(id: int, session: Session = Depends(get_session)):
    eq = session.get(Equipamento, id)
    if not eq:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    eq.ativo = False
    session.add(eq)
    session.commit()
