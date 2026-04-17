from datetime import date
from sqlmodel import Session, select
from app.models import Equipamento, AgendaPreventiva
from app.services.ollama_service import ollama_service


def gerar_agenda_pendente(session: Session):
    equipamentos = session.exec(
        select(Equipamento).where(
            Equipamento.ativo == True,
            Equipamento.intervalo_preventivo_dias != None,
        )
    ).all()

    for eq in equipamentos:
        pendente = session.exec(
            select(AgendaPreventiva).where(
                AgendaPreventiva.equipamento_id == eq.id,
                AgendaPreventiva.status == "pendente",
            )
        ).first()
        if pendente:
            continue

        ultima = session.exec(
            select(AgendaPreventiva)
            .where(
                AgendaPreventiva.equipamento_id == eq.id,
                AgendaPreventiva.status == "executado",
            )
            .order_by(AgendaPreventiva.data_executada.desc())
        ).first()

        hoje = date.today()
        deve_agendar = False
        data_devida = hoje

        if ultima is None:
            deve_agendar = True
        elif ultima.data_executada:
            from datetime import timedelta
            proxima = ultima.data_executada + timedelta(days=eq.intervalo_preventivo_dias)
            if hoje >= proxima:
                deve_agendar = True
                data_devida = proxima

        if deve_agendar:
            nova = AgendaPreventiva(
                equipamento_id=eq.id,
                data_programada=data_devida,
                status="pendente",
            )
            session.add(nova)

    session.commit()


async def gerar_checklist(equipamento: Equipamento) -> str:
    prompt = (
        f"Gere um checklist de manutenção preventiva para {equipamento.tipo} no setor {equipamento.setor}. "
        "Retorne apenas uma lista numerada com 5 a 8 itens concretos e específicos."
    )
    return await ollama_service.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="Você é um técnico especialista em manutenção de equipamentos hospitalares.",
    )
