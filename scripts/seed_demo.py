"""
Seed script — populates 3Notes.AI with realistic demo data.
Idempotent: safe to run multiple times.

Seeds:
  - 8 equipamentos
  - 6 chamados (2 resolvidos com .md, 1 em andamento, 2 abertos, 1 critico)
  - 3 agenda items
  - 2 manuais tecnicos + 1 protocolo em knowledge/
  - Tudo indexado no ChromaDB (requer Ollama + nomic-embed-text)
"""
import sys
import os
import json
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, date, timedelta
from pathlib import Path
from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models import Equipamento, Chamado, AgendaPreventiva, FonteConhecimento

create_db_and_tables()

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "./knowledge")

# --- Equipamentos ---

EQUIPAMENTOS = [
    dict(patrimonio="VM-001", descricao="Ventilador mecanico", tipo="Ventilador mecanico", setor="UTI", localizacao="UTI - Leito 3", criticidade_base="critico", intervalo_preventivo_dias=15),
    dict(patrimonio="MM-002", descricao="Monitor multiparametrico", tipo="Monitor multiparametrico", setor="UTI", localizacao="UTI - Leito 5", criticidade_base="critico", intervalo_preventivo_dias=30),
    dict(patrimonio="AC-003", descricao="Autoclave", tipo="Autoclave", setor="Centro Cirurgico", localizacao="Centro Cirurgico - Sala de esterilizacao", criticidade_base="alto", intervalo_preventivo_dias=30),
    dict(patrimonio="DF-004", descricao="Desfibrilador", tipo="Desfibrilador", setor="Emergencia", localizacao="Emergencia - Sala de trauma", criticidade_base="critico", intervalo_preventivo_dias=60),
    dict(patrimonio="BI-005", descricao="Bomba de infusao", tipo="Bomba de infusao", setor="UTI", localizacao="UTI - Leito 7", criticidade_base="alto", intervalo_preventivo_dias=30),
    dict(patrimonio="RX-006", descricao="Raio-X portatil", tipo="Raio-X portatil", setor="Radiologia", localizacao="Radiologia - Sala 2", criticidade_base="medio", intervalo_preventivo_dias=90),
    dict(patrimonio="OP-007", descricao="Oximetro de pulso", tipo="Oximetro de pulso", setor="Enfermaria", localizacao="Enfermaria - Ala B", criticidade_base="medio", intervalo_preventivo_dias=60),
    dict(patrimonio="RS-008", descricao="Respirador", tipo="Respirador", setor="UTI", localizacao="UTI - Leito 9", criticidade_base="critico", intervalo_preventivo_dias=15),
]

CHAMADOS_SEED = [
    dict(
        patrimonio="VM-001", tipo="corretivo", status="aberto",
        criticidade_sugerida="critico", criticidade_confirmada="critico",
        aberto_por="Maria Silva", setor_reportador="UTI",
        descricao="Ventilador emitindo alarme sonoro continuo e nao mantem pressao configurada. Paciente em uso.",
        criado_em=datetime.utcnow() - timedelta(hours=3),
    ),
    dict(
        patrimonio="DF-004", tipo="corretivo", status="aberto",
        criticidade_sugerida="critico",
        aberto_por="Joao Santos", setor_reportador="Emergencia",
        descricao="Desfibrilador nao carrega. Tela apresenta erro E-07 ao ligar.",
        criado_em=datetime.utcnow() - timedelta(hours=1, minutes=30),
    ),
    dict(
        patrimonio="AC-003", tipo="corretivo", status="em_andamento",
        criticidade_sugerida="alto", criticidade_confirmada="alto",
        aberto_por="Ana Ferreira", setor_reportador="Centro Cirurgico",
        descricao="Autoclave nao pressuriza ate o nivel correto. Ciclo interrompido na metade.",
        criado_em=datetime.utcnow() - timedelta(hours=5),
    ),
    dict(
        patrimonio="BI-005", tipo="corretivo", status="resolvido",
        criticidade_sugerida="alto", criticidade_confirmada="alto",
        aberto_por="Carlos Lima", setor_reportador="UTI",
        descricao="Bomba de infusao travada na tela de inicializacao. Alarme de oclusao (codigo E05). Nao reconhece o equipo.",
        resolucao="Reinicializacao de fabrica e substituicao do sensor de equipo. Troca do equipo descartavel. Equipamento operacional.",
        criado_em=datetime.utcnow() - timedelta(days=2),
        fechado_em=datetime.utcnow() - timedelta(days=1, hours=20),
    ),
    dict(
        patrimonio="RX-006", tipo="corretivo", status="resolvido",
        criticidade_sugerida="medio", criticidade_confirmada="medio",
        aberto_por="Paula Gomes", setor_reportador="Radiologia",
        descricao="Raio-X portatil com bateria nao carregando. Uso limitado ao cabo.",
        resolucao="Substituicao da bateria interna (modelo 12V 7Ah). Equipamento totalmente operacional.",
        criado_em=datetime.utcnow() - timedelta(days=5),
        fechado_em=datetime.utcnow() - timedelta(days=4, hours=16),
    ),
    dict(
        patrimonio="MM-002", tipo="preventivo", status="aberto",
        criticidade_sugerida="medio",
        aberto_por="Sistema", setor_reportador="UTI",
        descricao="Manutencao preventiva programada - 30 dias.",
        criado_em=datetime.utcnow() - timedelta(hours=2),
    ),
]

AGENDA_SEED = [
    dict(patrimonio="VM-001", data_programada=date.today() - timedelta(days=3), status="pendente"),
    dict(patrimonio="RS-008", data_programada=date.today() + timedelta(days=5), status="pendente"),
    dict(patrimonio="AC-003", data_programada=date.today() + timedelta(days=12), status="pendente"),
]


def md_chamado_bi005(chamado_id: int) -> str:
    ano = datetime.utcnow().year
    agora = (datetime.utcnow() - timedelta(days=1, hours=20)).isoformat(timespec='seconds')
    criado = (datetime.utcnow() - timedelta(days=2)).isoformat(timespec='seconds')
    return f"""---
id: CHM-{ano}-{chamado_id:04d}
titulo: "Bomba de Infusao BI-005 - Alarme de oclusao continuo"
tags: ["bomba-infusao", "alarme", "oclusao", "uti", "sensor-equipo", "e05"]
patrimonio: BI-005
setor: UTI
criticidade: alto
status: resolvido
aberto_por: Carlos Lima
setor_reportador: UTI
criado_em: {criado}
resolvido_em: {agora}
---

## Problema

Bomba de infusao BI-005 (UTI - Leito 7) travada na tela de inicializacao com alarme de oclusao codigo E05.
Equipamento nao reconhece o equipo descartavel. Paciente em necessidade de sedacao continua.

## Conversa

**Usuario:** A bomba de infusao da UTI esta com alarme e nao infunde.

**Assistente:** Qual o codigo do alarme mostrado no display?

**Usuario:** Aparece E05 e a bomba nao reconhece o equipo.

**Assistente:** Isso indica falha no sensor de oclusao ou equipo com defeito. Confirma que e a BI-005 no Leito 7?

## Tags sugeridas

`bomba-infusao`, `alarme`, `oclusao`, `uti`, `sensor-equipo`, `e05`

## Resolucao

Reinicializacao de fabrica e substituicao do sensor de equipo. Troca do equipo descartavel.
Equipamento operacional apos procedimento.

**Tecnico responsavel:** Carlos Lima
**Resolvido em:** {agora}
"""


def md_chamado_rx006(chamado_id: int) -> str:
    ano = datetime.utcnow().year
    agora = (datetime.utcnow() - timedelta(days=4, hours=16)).isoformat(timespec='seconds')
    criado = (datetime.utcnow() - timedelta(days=5)).isoformat(timespec='seconds')
    return f"""---
id: CHM-{ano}-{chamado_id:04d}
titulo: "Raio-X Portatil RX-006 - Bateria nao carrega"
tags: ["raio-x", "bateria", "carregamento", "radiologia", "portatil"]
patrimonio: RX-006
setor: Radiologia
criticidade: medio
status: resolvido
aberto_por: Paula Gomes
setor_reportador: Radiologia
criado_em: {criado}
resolvido_em: {agora}
---

## Problema

Raio-X portatil RX-006 com bateria nao carregando. Uso limitado exclusivamente ao cabo de alimentacao.
Equipamento sem autonomia para deslocamento entre setores.

## Conversa

**Usuario:** O raio-x portatil nao carrega a bateria mais.

**Assistente:** Ha quanto tempo esse problema esta ocorrendo?

**Usuario:** Faz uns 3 dias. A bateria fica em 0% mesmo na tomada.

## Tags sugeridas

`raio-x`, `bateria`, `carregamento`, `radiologia`, `portatil`

## Resolucao

Substituicao da bateria interna (modelo 12V 7Ah). Equipamento totalmente operacional apos troca.
Bateria antiga descartada conforme protocolo de residuos eletronicos hospitalares.

**Tecnico responsavel:** Paula Gomes
**Resolvido em:** {agora}
"""


MANUAL_BOMBA_INFUSAO = """# Manual de Manutencao - Bombas de Infusao Fresenius Agilia

## 1. Alarmes comuns

### Alarme E05 - Oclusao detectada
Causa: Sensor de pressao detectou obstrucao no fluxo do equipo.
Procedimento:
1. Verificar se o equipo esta corretamente instalado
2. Inspecionar o equipo por dobras ou clamps fechados
3. Substituir o equipo descartavel
4. Se persistir: reinicializar (hold power 5 segundos)
5. Se retornar: substituir sensor de oclusao (FR-SENS-005)

### Alarme E12 - Bateria fraca
Causa: Bateria interna abaixo de 20%.
Procedimento: Conectar a tomada por minimo 4 horas.

## 2. Manutencao preventiva (intervalo: 30 dias)

Checklist:
- Verificar mecanismo de clamp (desgaste nas bordas)
- Testar sensor de oclusao com equipo de teste calibrado
- Verificar integridade do cabo de alimentacao
- Checar bateria: capacidade minima 80% da nominal
- Limpar interface com alcool 70GL
- Verificar display e botoes
- Registrar numero de ciclos (limite: 10.000 ciclos por sensor)

## 3. Calibracao do sensor de pressao

Fazer a cada 6 meses ou apos troca do sensor.
Instrumento: Manometro de referencia certificado (0-300 mmHg).
Codigo de acesso modo tecnico: 4-4-8-8

## 4. Pecas de reposicao criticas

| Peca | Codigo | Vida util estimada |
|---|---|---|
| Sensor de oclusao | FR-SENS-005 | 10.000 ciclos |
| Bateria interna | FR-BAT-12V | 2 anos |
| Motor peristaltico | FR-MOT-001 | 5 anos |
"""

PROTOCOLO_MANUTENCAO = """# Protocolo de Manutencao Corretiva - Hospital Regional Norte
Versao 2.1 | Vigencia: Janeiro 2026

## 1. Classificacao de prioridade

### Nivel Critico (SLA: 2 horas)
Equipamentos em uso direto com paciente sem substituto disponivel.
Exemplos: Ventilador mecanico em uso, monitor cardiaco unico na UTI, bomba de infusao com medicacao ativa.

Acao imediata:
- Notificar chefe de plantao
- Contatar tecnico de sobreaviso
- Registrar no 3Notes.AI com criticidade CRITICO
- Se sem solucao em 1h: acionar empresa terceirizada de emergencia

### Nivel Alto (SLA: 8 horas)
Equipamentos importantes com substituto disponivel.
Acao: Tecnico de plantao atende no mesmo turno.

### Nivel Medio (SLA: 24 horas)
Equipamentos de suporte com substituto.
Acao: Tecnico agenda atendimento ate o proximo dia util.

### Nivel Baixo (SLA: 72 horas)
Equipamentos auxiliares com baixo impacto clinico imediato.
Acao: Fila normal de manutencao.

## 2. Registro obrigatorio

Todo chamado deve ser registrado no sistema 3Notes.AI com:
- Patrimonio do equipamento
- Descricao detalhada do problema
- Sintomas observados (sons, codigos de erro, comportamento)
- Nome de quem reportou
- Setor de origem

## 3. Resolucao e encerramento

Ao resolver, o tecnico deve registrar:
- Causa raiz identificada
- Procedimento executado
- Pecas substituidas (com codigo e numero de serie)
- Tempo de atendimento
- Recomendacoes para prevencao futura

## 4. Rastreabilidade

Todos os registros ficam na base de conhecimento do 3Notes.AI.
O sistema aprende com cada chamado resolvido e sugere solucoes baseadas em historico.
Isso elimina a perda de conhecimento institucional a cada troca de turno ou saida de funcionario.
"""


async def indexar_arquivo(md_path: str, metadata: dict) -> bool:
    try:
        from app.services.rag_service import rag_service
        await rag_service.indexar_documento(md_path, metadata)
        return True
    except Exception as e:
        print(f"    [!] {Path(md_path).name}: {e}")
        return False


def registrar_fonte(session: Session, titulo: str, tipo: str, arquivo_path: str, tags: list) -> None:
    existing = session.exec(
        select(FonteConhecimento).where(FonteConhecimento.arquivo_path == arquivo_path)
    ).first()
    if existing:
        return
    fonte = FonteConhecimento(
        titulo=titulo,
        tipo=tipo,
        arquivo_path=arquivo_path,
        tags=json.dumps(tags, ensure_ascii=False),
    )
    session.add(fonte)
    session.commit()


def seed():
    with Session(engine) as session:
        print("--- Equipamentos ---")
        eq_map = {}
        for data in EQUIPAMENTOS:
            existing = session.exec(select(Equipamento).where(Equipamento.patrimonio == data["patrimonio"])).first()
            if not existing:
                eq = Equipamento(**data)
                session.add(eq)
                session.flush()
                eq_map[data["patrimonio"]] = eq.id
                print(f"  [+] {data['patrimonio']} - {data['descricao']}")
            else:
                eq_map[data["patrimonio"]] = existing.id
                print(f"  [=] {data['patrimonio']} ja existe")
        session.commit()

        print("\n--- Chamados ---")
        chamado_map = {}
        for c in CHAMADOS_SEED:
            pat = c.pop("patrimonio")
            eq_id = eq_map.get(pat)
            if not eq_id:
                continue
            existing = session.exec(
                select(Chamado).where(Chamado.equipamento_id == eq_id, Chamado.descricao == c["descricao"])
            ).first()
            if not existing:
                chamado = Chamado(equipamento_id=eq_id, **c)
                session.add(chamado)
                session.flush()
                chamado_map[pat] = chamado.id
                print(f"  [+] {pat}: {c['descricao'][:50]}...")
            else:
                chamado_map[pat] = existing.id
                print(f"  [=] {pat} ja existe (id={existing.id})")
        session.commit()

        print("\n--- Agenda ---")
        for a in AGENDA_SEED:
            pat = a.pop("patrimonio")
            eq_id = eq_map.get(pat)
            if not eq_id:
                continue
            existing = session.exec(
                select(AgendaPreventiva).where(
                    AgendaPreventiva.equipamento_id == eq_id,
                    AgendaPreventiva.data_programada == a["data_programada"],
                )
            ).first()
            if not existing:
                agenda = AgendaPreventiva(equipamento_id=eq_id, **a)
                session.add(agenda)
                print(f"  [+] Agenda {pat} - {a['data_programada']}")
            else:
                print(f"  [=] Agenda {pat} ja existe")
        session.commit()

        print("\n--- Knowledge Base (.md files) ---")
        knowledge_root = Path(KNOWLEDGE_DIR)
        (knowledge_root / "chamados").mkdir(parents=True, exist_ok=True)
        (knowledge_root / "manuais").mkdir(parents=True, exist_ok=True)
        (knowledge_root / "protocolos").mkdir(parents=True, exist_ok=True)

        arquivos = []
        ano = datetime.utcnow().year

        # Chamado BI-005 resolvido
        bi_id = chamado_map.get("BI-005")
        if bi_id:
            bi_path = knowledge_root / "chamados" / f"CHM-{ano}-{bi_id:04d}.md"
            if not bi_path.exists():
                bi_path.write_text(md_chamado_bi005(bi_id), encoding="utf-8")
                print(f"  [+] {bi_path.name}")
            else:
                print(f"  [=] {bi_path.name} ja existe")
            with Session(engine) as s2:
                ch = s2.get(Chamado, bi_id)
                if ch and not ch.md_path:
                    ch.md_path = str(bi_path)
                    s2.add(ch)
                    s2.commit()
            meta = {"titulo": f"CHM-{ano}-{bi_id:04d} Bomba de Infusao BI-005 - Alarme de oclusao",
                    "tipo": "chamado_resolvido", "arquivo_path": str(bi_path)}
            arquivos.append((str(bi_path), meta))
            registrar_fonte(session, meta["titulo"], "chamado_resolvido", str(bi_path),
                          ["bomba-infusao", "alarme", "oclusao", "uti", "e05"])

        # Chamado RX-006 resolvido
        rx_id = chamado_map.get("RX-006")
        if rx_id:
            rx_path = knowledge_root / "chamados" / f"CHM-{ano}-{rx_id:04d}.md"
            if not rx_path.exists():
                rx_path.write_text(md_chamado_rx006(rx_id), encoding="utf-8")
                print(f"  [+] {rx_path.name}")
            else:
                print(f"  [=] {rx_path.name} ja existe")
            with Session(engine) as s2:
                ch = s2.get(Chamado, rx_id)
                if ch and not ch.md_path:
                    ch.md_path = str(rx_path)
                    s2.add(ch)
                    s2.commit()
            meta = {"titulo": f"CHM-{ano}-{rx_id:04d} Raio-X Portatil RX-006 - Bateria nao carrega",
                    "tipo": "chamado_resolvido", "arquivo_path": str(rx_path)}
            arquivos.append((str(rx_path), meta))
            registrar_fonte(session, meta["titulo"], "chamado_resolvido", str(rx_path),
                          ["raio-x", "bateria", "carregamento", "radiologia"])

        # Manual tecnico
        manual_path = knowledge_root / "manuais" / "manual-bombas-infusao-fresenius.md"
        if not manual_path.exists():
            manual_path.write_text(MANUAL_BOMBA_INFUSAO, encoding="utf-8")
            print(f"  [+] {manual_path.name}")
        else:
            print(f"  [=] {manual_path.name} ja existe")
        meta_m = {"titulo": "Manual de Manutencao - Bombas de Infusao Fresenius Agilia",
                  "tipo": "manual", "arquivo_path": str(manual_path)}
        arquivos.append((str(manual_path), meta_m))
        registrar_fonte(session, meta_m["titulo"], "manual", str(manual_path),
                      ["bomba-infusao", "fresenius", "agilia", "manutencao"])

        # Protocolo
        prot_path = knowledge_root / "protocolos" / "protocolo-manutencao-corretiva.md"
        if not prot_path.exists():
            prot_path.write_text(PROTOCOLO_MANUTENCAO, encoding="utf-8")
            print(f"  [+] {prot_path.name}")
        else:
            print(f"  [=] {prot_path.name} ja existe")
        meta_p = {"titulo": "Protocolo de Manutencao Corretiva - Hospital Regional Norte",
                  "tipo": "protocolo", "arquivo_path": str(prot_path)}
        arquivos.append((str(prot_path), meta_p))
        registrar_fonte(session, meta_p["titulo"], "protocolo", str(prot_path),
                      ["protocolo", "manutencao-corretiva", "sla"])

        print("\n--- ChromaDB indexacao ---")
        print("  (requer Ollama rodando com nomic-embed-text)")

        async def indexar_tudo():
            for caminho, meta in arquivos:
                ok = await indexar_arquivo(caminho, meta)
                s = "[+]" if ok else "[!]"
                print(f"  {s} {Path(caminho).name}")

        try:
            asyncio.run(indexar_tudo())
        except Exception as e:
            print(f"  [!] Erro: {e}")
            print("      Execute com Ollama rodando para indexar.")

    print("\nSeed concluido.")
    print("Acesse: http://localhost:8000/static/reporter.html")
    print("        http://localhost:8000/static/dashboard.html")


if __name__ == "__main__":
    print("3Notes.AI - Populando base de dados e knowledge base...\n")
    seed()
