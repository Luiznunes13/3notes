from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class Equipamento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patrimonio: str = Field(unique=True)
    descricao: str
    tipo: str
    setor: str
    localizacao: str
    criticidade_base: str = Field(default="medio")
    intervalo_preventivo_dias: Optional[int] = None
    ativo: bool = Field(default=True)
    criado_em: datetime = Field(default_factory=datetime.utcnow)

    chamados: list["Chamado"] = Relationship(back_populates="equipamento")
    agendas: list["AgendaPreventiva"] = Relationship(back_populates="equipamento")


class Chamado(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    equipamento_id: int = Field(foreign_key="equipamento.id")
    tipo: str  # "corretivo" | "preventivo"
    status: str = Field(default="aberto")
    criticidade_sugerida: Optional[str] = None
    criticidade_confirmada: Optional[str] = None
    aberto_por: str
    setor_reportador: str
    descricao: str
    conversa_json: Optional[str] = None
    resolucao: Optional[str] = None
    md_path: Optional[str] = None
    # --- Validação pelo master ---
    validado: bool = Field(default=False)
    validado_por: Optional[str] = None
    validado_em: Optional[datetime] = None
    criado_em: datetime = Field(default_factory=datetime.utcnow)
    fechado_em: Optional[datetime] = None

    equipamento: Optional[Equipamento] = Relationship(back_populates="chamados")
    historico: list["HistoricoStatus"] = Relationship(back_populates="chamado")


class AgendaPreventiva(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    equipamento_id: int = Field(foreign_key="equipamento.id")
    data_programada: date
    data_executada: Optional[date] = None
    tecnico: Optional[str] = None
    checklist_json: Optional[str] = None
    status: str = Field(default="pendente")

    equipamento: Optional[Equipamento] = Relationship(back_populates="agendas")


class HistoricoStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chamado_id: int = Field(foreign_key="chamado.id")
    status_anterior: str
    status_novo: str
    alterado_por: str
    alterado_em: datetime = Field(default_factory=datetime.utcnow)
    observacao: Optional[str] = None

    chamado: Optional[Chamado] = Relationship(back_populates="historico")


class FonteConhecimento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    tipo: str  # "chamado_resolvido" | "manual" | "protocolo" | "documento"
    arquivo_path: str  # caminho relativo do .md
    tags: Optional[str] = None  # JSON array como string
    indexado_em: datetime = Field(default_factory=datetime.utcnow)
    ativo: bool = Field(default=True)


# --- Pydantic schemas ---

class EquipamentoCreate(SQLModel):
    patrimonio: str
    descricao: str
    tipo: str
    setor: str
    localizacao: str
    criticidade_base: str = "medio"
    intervalo_preventivo_dias: Optional[int] = None
    ativo: bool = True


class EquipamentoRead(SQLModel):
    id: int
    patrimonio: str
    descricao: str
    tipo: str
    setor: str
    localizacao: str
    criticidade_base: str
    intervalo_preventivo_dias: Optional[int]
    ativo: bool
    criado_em: datetime


class EquipamentoUpdate(SQLModel):
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    setor: Optional[str] = None
    localizacao: Optional[str] = None
    criticidade_base: Optional[str] = None
    intervalo_preventivo_dias: Optional[int] = None
    ativo: Optional[bool] = None


class ChamadoCreate(SQLModel):
    equipamento_id: int
    tipo: str
    aberto_por: str
    setor_reportador: str
    descricao: str
    criticidade_sugerida: Optional[str] = None
    conversa_json: Optional[str] = None


class ChamadoRead(SQLModel):
    id: int
    equipamento_id: int
    tipo: str
    status: str
    criticidade_sugerida: Optional[str]
    criticidade_confirmada: Optional[str]
    aberto_por: str
    setor_reportador: str
    descricao: str
    resolucao: Optional[str]
    md_path: Optional[str]
    validado: bool
    validado_por: Optional[str]
    validado_em: Optional[datetime]
    criado_em: datetime
    fechado_em: Optional[datetime]


class ChamadoEdit(SQLModel):
    """Schema para edição pelo master antes de validar."""
    descricao: Optional[str] = None
    criticidade_sugerida: Optional[str] = None
    setor_reportador: Optional[str] = None
    aberto_por: Optional[str] = None
    tags_finais: Optional[list[str]] = None


class AgendaPreventivaRead(SQLModel):
    id: int
    equipamento_id: int
    data_programada: date
    data_executada: Optional[date]
    tecnico: Optional[str]
    checklist_json: Optional[str]
    status: str


class HistoricoStatusRead(SQLModel):
    id: int
    chamado_id: int
    status_anterior: str
    status_novo: str
    alterado_por: str
    alterado_em: datetime
    observacao: Optional[str]


class FonteConhecimentoRead(SQLModel):
    id: int
    titulo: str
    tipo: str
    arquivo_path: str
    tags: Optional[str]
    indexado_em: datetime
    ativo: bool
