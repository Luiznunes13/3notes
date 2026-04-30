"""
seed_volume.py — Gera 50 chamados hospitalares realistas para demonstrar o RAG.

Todos os chamados são criados como já resolvidos, validados e embeddados no ChromaDB.
Simula ~2 anos de histórico operacional de um hospital de médio porte.

Uso:
    cd 3notes
    python scripts/seed_volume.py

Requer Ollama com nomic-embed-text rodando para indexar no ChromaDB.
Os chamados SQL são criados independente do Ollama.
"""
import sys, os, json, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from pathlib import Path
from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models import Equipamento, Chamado, FonteConhecimento

create_db_and_tables()

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "./knowledge")
ANO = datetime.utcnow().year

# ─────────────────────────────────────────────────────────
#  EQUIPAMENTOS (12 equipamentos em 6 setores)
# ─────────────────────────────────────────────────────────
EQUIPAMENTOS = [
    dict(patrimonio="VM-001", descricao="Ventilador Mecânico Dräger Evita 4", tipo="Ventilador Mecânico",
         setor="UTI", localizacao="UTI - Leito 3", criticidade_base="critico", intervalo_preventivo_dias=15),
    dict(patrimonio="VM-002", descricao="Ventilador Mecânico Hamilton C3", tipo="Ventilador Mecânico",
         setor="UTI", localizacao="UTI - Leito 6", criticidade_base="critico", intervalo_preventivo_dias=15),
    dict(patrimonio="MM-001", descricao="Monitor Multiparamétrico Philips IntelliVue", tipo="Monitor Multiparamétrico",
         setor="UTI", localizacao="UTI - Leito 5", criticidade_base="critico", intervalo_preventivo_dias=30),
    dict(patrimonio="MM-002", descricao="Monitor Multiparamétrico Mindray BeneVision", tipo="Monitor Multiparamétrico",
         setor="Emergência", localizacao="Emergência - Box 2", criticidade_base="critico", intervalo_preventivo_dias=30),
    dict(patrimonio="BI-001", descricao="Bomba de Infusão Fresenius Agilia", tipo="Bomba de Infusão",
         setor="UTI", localizacao="UTI - Leito 7", criticidade_base="alto", intervalo_preventivo_dias=30),
    dict(patrimonio="BI-002", descricao="Bomba de Infusão BD Alaris", tipo="Bomba de Infusão",
         setor="Maternidade", localizacao="Maternidade - Sala 3", criticidade_base="alto", intervalo_preventivo_dias=30),
    dict(patrimonio="BI-003", descricao="Bomba de Infusão Baxter Sigma Spectrum", tipo="Bomba de Infusão",
         setor="UTI", localizacao="UTI - Leito 2", criticidade_base="alto", intervalo_preventivo_dias=30),
    dict(patrimonio="AC-001", descricao="Autoclave Vertical Cristofoli", tipo="Autoclave",
         setor="Centro Cirúrgico", localizacao="Centro Cirúrgico - Sala de Esterilização", criticidade_base="alto", intervalo_preventivo_dias=30),
    dict(patrimonio="DF-001", descricao="Desfibrilador Zoll R Series", tipo="Desfibrilador",
         setor="Emergência", localizacao="Emergência - Sala de Trauma", criticidade_base="critico", intervalo_preventivo_dias=60),
    dict(patrimonio="RX-001", descricao="Raio-X Portátil GE AMX 4+", tipo="Raio-X Portátil",
         setor="Radiologia", localizacao="Radiologia - Sala 1", criticidade_base="medio", intervalo_preventivo_dias=90),
    dict(patrimonio="OP-001", descricao="Oxímetro de Pulso Nonin 7500", tipo="Oxímetro de Pulso",
         setor="Enfermaria", localizacao="Enfermaria - Ala B", criticidade_base="medio", intervalo_preventivo_dias=60),
    dict(patrimonio="RS-001", descricao="Respirador de Transporte Drager Oxylog 3000", tipo="Respirador",
         setor="UTI", localizacao="UTI - Corredor", criticidade_base="critico", intervalo_preventivo_dias=15),
]

# ─────────────────────────────────────────────────────────
#  50 CHAMADOS RESOLVIDOS (problema + resolução detalhada)
# ─────────────────────────────────────────────────────────
CHAMADOS = [

    # ── VENTILADOR MECÂNICO ──────────────────────────────
    dict(patrimonio="VM-001", aberto_por="Maria Silva", setor_reportador="UTI",
         dias_atras=420, horas_resolucao=2,
         descricao="Ventilador emitindo alarme ALTO PEEP contínuo. Pressão de pico acima de 40 cmH2O sem alteração no paciente. Display mostra PSET diferente do configurado.",
         resolucao="Investigado e encontrado condensado d'água no circuito do paciente causando aumento de resistência. Esvaziado condensado, substituído circuito ventilatório (código DR-CIR-001). Reajustados parâmetros PEEP=8 e Pmax=35. Equipamento operacional.",
         tags=["ventilador", "alarme", "peep", "circuito", "condensado", "pressao-pico"],
         criticidade="critico"),

    dict(patrimonio="VM-001", aberto_por="João Santos", setor_reportador="UTI",
         dias_atras=380, horas_resolucao=3,
         descricao="Ventilador não mantém FiO2 configurado em 60%. Sensor de oxigênio indicando leitura errática entre 21% e 95%.",
         resolucao="Sensor de O2 com vida útil esgotada (>18 meses). Substituído sensor (DR-O2-004, lote 2024-11). Calibração realizada com O2 medicinal 100%. FiO2 estável após troca. Monitorar próxima calibração em 12 meses.",
         tags=["ventilador", "fio2", "sensor-oxigenio", "calibracao", "uti"],
         criticidade="critico"),

    dict(patrimonio="VM-002", aberto_por="Ana Ferreira", setor_reportador="UTI",
         dias_atras=350, horas_resolucao=1,
         descricao="Tela do ventilador piscando e apagando intermitentemente. Modo de operação mantido mas equipe sem visibilidade dos parâmetros.",
         resolucao="Cabo flat do display internamente com mau contato. Reaperto do conector e limpeza dos terminais com contato elétrico spray. Display estável após procedimento. Se reincidir, trocar cabo flat (HM-FLAT-C3).",
         tags=["ventilador", "display", "tela", "cabo", "mau-contato"],
         criticidade="alto"),

    dict(patrimonio="VM-002", aberto_por="Carlos Lima", setor_reportador="UTI",
         dias_atras=290, horas_resolucao=4,
         descricao="Ruído mecânico intenso proveniente do módulo de fluxo. Sons de raspagem audíveis a 1 metro de distância.",
         resolucao="Rolamento do motor do blower com desgaste avançado. Substituído motor blower completo (HM-BLW-002). Lubrificação dos rolamentos auxiliares. Equipamento silencioso e operacional após troca.",
         tags=["ventilador", "ruido", "motor", "blower", "rolamento"],
         criticidade="alto"),

    dict(patrimonio="VM-001", aberto_por="Maria Silva", setor_reportador="UTI",
         dias_atras=240, horas_resolucao=2,
         descricao="Alarme APNEIA disparando mesmo com o paciente respirando espontaneamente. Trigger de fluxo não responde.",
         resolucao="Sensor de fluxo interno obstruído por secreção. Desmontagem e limpeza do sensor com solução enzimática. Recalibração do trigger de fluxo (limiar: 2 L/min). Teste de apneia realizado com sucesso.",
         tags=["ventilador", "alarme", "apneia", "trigger", "sensor-fluxo", "calibracao"],
         criticidade="critico"),

    # ── MONITOR MULTIPARAMÉTRICO ─────────────────────────
    dict(patrimonio="MM-001", aberto_por="Paula Gomes", setor_reportador="UTI",
         dias_atras=410, horas_resolucao=1,
         descricao="SpO2 não lê. Sensor posicionado corretamente no dedo mas valor aparece como --- com alarme intermitente.",
         resolucao="Sensor de SpO2 com cabo danificado na junção com o conector. Substituído sensor (PH-SPO2-INF) por novo. Leitura estável 98% em paciente teste. Sensor antigo descartado.",
         tags=["monitor", "spo2", "sensor", "cabo", "alarme"],
         criticidade="critico"),

    dict(patrimonio="MM-001", aberto_por="Roberto Alves", setor_reportador="UTI",
         dias_atras=370, horas_resolucao=1,
         descricao="ECG com ruído intenso em todas as derivações. Traçado ilegível, impossível avaliar ritmo cardíaco.",
         resolucao="Cabos de ECG oxidados e com isolamento comprometido. Substituição completa do kit de cabos (PH-ECG-5V). Aterramento do equipamento verificado (corrente de fuga < 10µA). Traçado limpo após troca.",
         tags=["monitor", "ecg", "ruido", "cabo", "aterramento"],
         criticidade="critico"),

    dict(patrimonio="MM-002", aberto_por="Sandra Costa", setor_reportador="Emergência",
         dias_atras=320, horas_resolucao=2,
         descricao="Monitor emitindo alarme de bateria fraca constantemente mesmo quando conectado à rede elétrica.",
         resolucao="Bateria interna sulfatada e não retendo carga (tensão: 8V, nominal: 12V). Substituída bateria (MD-BAT-12-7). Equipamento testado 4h sem rede e bateria manteve carga > 80%.",
         tags=["monitor", "bateria", "alarme", "carga", "emergencia"],
         criticidade="medio"),

    dict(patrimonio="MM-002", aberto_por="Fernanda Lima", setor_reportador="Emergência",
         dias_atras=260, horas_resolucao=3,
         descricao="NIBP (pressão não-invasiva) com medições inconsistentes. Valores diferem até 30 mmHg de esfigmomanômetro calibrado.",
         resolucao="Manguito com vazamento interno (borracha ressecada). Substituído manguito adulto (MD-MNG-ADU). Calibração cruzada realizada: diferença < 3 mmHg após troca. Bomba de insuflação dentro dos parâmetros.",
         tags=["monitor", "nibp", "pressao", "manguito", "calibracao"],
         criticidade="alto"),

    dict(patrimonio="MM-001", aberto_por="José Oliveira", setor_reportador="UTI",
         dias_atras=200, horas_resolucao=2,
         descricao="Tela do monitor com área queimada no canto inferior esquerdo. 20% da área de visualização comprometida.",
         resolucao="Display com burn-in irreversível. Substituição do módulo de display (PH-DISP-IV). Configurado protetor de tela pós-troca para evitar reincidência.",
         tags=["monitor", "display", "tela", "burn-in", "uti"],
         criticidade="medio"),

    # ── BOMBA DE INFUSÃO ─────────────────────────────────
    dict(patrimonio="BI-001", aberto_por="Carlos Lima", setor_reportador="UTI",
         dias_atras=430, horas_resolucao=1,
         descricao="Bomba de infusão com alarme E05 de oclusão contínuo. Equipo corretamente instalado. Medicação não infundindo. Paciente com sedação em risco.",
         resolucao="Sensor de oclusão obstruído por resíduo de medicação cristalizada. Limpeza com solução salina pressurizada. Calibração do sensor (pressão limiar: 150 mmHg). Equipamento operacional após limpeza.",
         tags=["bomba-infusao", "alarme", "oclusao", "e05", "sensor", "uti"],
         criticidade="critico"),

    dict(patrimonio="BI-001", aberto_por="Ana Ferreira", setor_reportador="UTI",
         dias_atras=390, horas_resolucao=1,
         descricao="Bomba não infunde mesmo sem alarme. Display mostra volume infundido avançando mas paciente não recebe medicação.",
         resolucao="Mecanismo de clamp (rolete) com desgaste avançado não comprimindo o equipo adequadamente. Substituição do mecanismo de clamp (FR-CLAMP-001). Teste de infusão a 5, 10 e 50 mL/h realizado com sucesso.",
         tags=["bomba-infusao", "nao-infunde", "clamp", "rolete", "mecanismo"],
         criticidade="critico"),

    dict(patrimonio="BI-002", aberto_por="Lucia Mendes", setor_reportador="Maternidade",
         dias_atras=340, horas_resolucao=2,
         descricao="Bomba de infusão travada na tela de inicialização. Reinicializações manuais não resolvem. Erro 'SYSTEM FAULT' ao ligar.",
         resolucao="Firmware corrompido após queda de energia. Reinstalação do firmware v4.2.1 via cabo USB e software Alaris Point-of-Care. Reset de fábrica executado. Backup de configurações restaurado. Equipamento operacional.",
         tags=["bomba-infusao", "firmware", "system-fault", "inicializacao", "maternidade"],
         criticidade="alto"),

    dict(patrimonio="BI-003", aberto_por="Paulo Ribeiro", setor_reportador="UTI",
         dias_atras=300, horas_resolucao=1,
         descricao="Alarme E12 (bateria fraca) mesmo após 8h conectada. Bateria não carrega acima de 40%.",
         resolucao="Bateria interna (FR-BAT-12V) com 3 anos e capacidade degradada para 35% do nominal. Substituição da bateria. Carregamento completo verificado em 4h. Autonomia testada: 8h com carga moderada.",
         tags=["bomba-infusao", "bateria", "e12", "carregamento", "uti"],
         criticidade="medio"),

    dict(patrimonio="BI-001", aberto_por="Maria Silva", setor_reportador="UTI",
         dias_atras=250, horas_resolucao=2,
         descricao="Display da bomba mostrando valores espelhados/invertidos. Impossível configurar volume e velocidade com segurança.",
         resolucao="Problema no controlador de display (bit de orientação corrompido na EEPROM). Acesso ao modo técnico (código 4-4-8-8), reconfiguração da orientação do display. Equipamento operacional sem troca de peça.",
         tags=["bomba-infusao", "display", "eeprom", "configuracao", "modo-tecnico"],
         criticidade="alto"),

    dict(patrimonio="BI-002", aberto_por="Sandra Costa", setor_reportador="Maternidade",
         dias_atras=180, horas_resolucao=1,
         descricao="Bomba emite bipe aleatório a cada 2-3 minutos sem alarme associado. Interfere no ambiente da maternidade.",
         resolucao="Botão de silêncio de alarme com mau contato gerando falsos acionamentos. Limpeza com ar comprimido e álcool 70%. Teste de 2h sem bipes espúrios. Se reincidir, trocar módulo de teclado (BD-KB-001).",
         tags=["bomba-infusao", "bipe", "alarme-espurio", "botao", "mau-contato"],
         criticidade="baixo"),

    dict(patrimonio="BI-003", aberto_por="Roberto Alves", setor_reportador="UTI",
         dias_atras=150, horas_resolucao=3,
         descricao="Bomba com erro E05 recorrente. Já foi limpa 2 vezes mas erro retorna em 24-48h.",
         resolucao="Sensor de oclusão com desgaste permanente causando falsos positivos recorrentes. Substituição definitiva do sensor (FR-SENS-005). Instalado equipo de teste para verificação diária por 1 semana. Sem reincidência após troca.",
         tags=["bomba-infusao", "e05", "sensor-oclusao", "recorrente", "troca-sensor"],
         criticidade="alto"),

    # ── AUTOCLAVE ────────────────────────────────────────
    dict(patrimonio="AC-001", aberto_por="Carlos Lima", setor_reportador="Centro Cirúrgico",
         dias_atras=450, horas_resolucao=4,
         descricao="Autoclave não pressuriza até o nível correto (2,1 kgf/cm²). Ciclo interrompido automaticamente na metade. Toda a programação cirúrgica em risco.",
         resolucao="Gaxeta da câmara com ressecamento e trinca. Substituição da gaxeta de vedação (CR-GAX-210). Teste de 3 ciclos consecutivos com pressurização correta (2,1 kgf/cm² em 8min). Indicadores biológicos enviados para validação.",
         tags=["autoclave", "pressurizacao", "gaxeta", "vedacao", "centro-cirurgico"],
         criticidade="alto"),

    dict(patrimonio="AC-001", aberto_por="Ana Ferreira", setor_reportador="Centro Cirúrgico",
         dias_atras=360, horas_resolucao=3,
         descricao="Ciclo de esterilização com duração 40% maior que o esperado. Temperatura demorando para atingir 134°C.",
         resolucao="Resistência elétrica de aquecimento com degradação (~60% da potência nominal). Substituição da resistência (CR-RES-3KW). Filtro de entrada de água entupido (calcário). Limpeza do filtro com ácido cítrico. Ciclo normalizado: 134°C em 4min.",
         tags=["autoclave", "temperatura", "resistencia", "aquecimento", "filtro", "calcario"],
         criticidade="alto"),

    dict(patrimonio="AC-001", aberto_por="Paulo Ribeiro", setor_reportador="Centro Cirúrgico",
         dias_atras=270, horas_resolucao=2,
         descricao="Sensor de temperatura indicando leitura errática. Ciclos sendo cancelados por 'temperatura inconsistente'.",
         resolucao="Termopar interno com oxidação nos terminais. Limpeza dos contatos e substituição do termopar (CR-TEMP-001). Calibração com termômetro padrão certificado. Erro < 0,5°C em relação ao padrão.",
         tags=["autoclave", "sensor-temperatura", "termopar", "calibracao", "oxidacao"],
         criticidade="medio"),

    # ── DESFIBRILADOR ─────────────────────────────────────
    dict(patrimonio="DF-001", aberto_por="Fernanda Lima", setor_reportador="Emergência",
         dias_atras=440, horas_resolucao=3,
         descricao="Desfibrilador não carrega. Tela apresenta erro E-07 ao tentar carregar o capacitor. Equipamento essencial para sala de trauma.",
         resolucao="Capacitor principal com falha de isolamento. Substituição do capacitor eletrolítico (ZL-CAP-360J). Teste de carga completa realizado: 360J em 8 segundos (nominal: <10s). Equipamento certificado para uso.",
         tags=["desfibrilador", "nao-carrega", "e07", "capacitor", "emergencia"],
         criticidade="critico"),

    dict(patrimonio="DF-001", aberto_por="José Oliveira", setor_reportador="Emergência",
         dias_atras=380, horas_resolucao=2,
         descricao="Pás do desfibrilador com superfície de contato danificada (rachaduras no gel pad). Risco de arco elétrico.",
         resolucao="Pás adultas substituídas (ZL-PAS-ADU). Testada descarga controlada em dummy resistivo. Impedância de contato dentro do especificado. Antiga par de pás descartada conforme protocolo de equipamentos elétricos.",
         tags=["desfibrilador", "pas", "contato", "gel-pad", "seguranca"],
         criticidade="critico"),

    dict(patrimonio="DF-001", aberto_por="Maria Silva", setor_reportador="Emergência",
         dias_atras=290, horas_resolucao=1,
         descricao="Bateria do desfibrilador com indicador vermelho permanente. Autonomia insuficiente para uso sem rede.",
         resolucao="Bateria SLA (12V 18Ah) com 4 anos e capacidade < 50%. Substituição (ZL-BAT-18). Carga completa em 6h. Teste de autonomia: 4h sem rede com 50 descargas simuladas a 200J.",
         tags=["desfibrilador", "bateria", "autonomia", "sla"],
         criticidade="alto"),

    # ── RAIO-X PORTÁTIL ──────────────────────────────────
    dict(patrimonio="RX-001", aberto_por="Paula Gomes", setor_reportador="Radiologia",
         dias_atras=460, horas_resolucao=2,
         descricao="Bateria do raio-x portátil não carrega. Uso limitado ao cabo. Impossível realizar exames à beira do leito.",
         resolucao="Bateria 12V 7Ah com sulfatação interna. Substituição (GE-BAT-12-7). Carga completa verificada. Equipamento operacional com autonomia para 40+ exposições sem rede.",
         tags=["raio-x", "bateria", "carregamento", "portatil", "radiologia"],
         criticidade="medio"),

    dict(patrimonio="RX-001", aberto_por="Roberto Alves", setor_reportador="Radiologia",
         dias_atras=390, horas_resolucao=4,
         descricao="Imagens com artefatos em forma de listras horizontais. Técnica de exposição correta, problema na captação.",
         resolucao="Detector digital com pixels mortos em linha horizontal (degradação do CCD). Limpeza do painel detector com solução antiestática. Recalibração de pixels defeituosos via software GE Service. 95% dos pixels recuperados, qualidade de imagem aprovada.",
         tags=["raio-x", "imagem", "artefato", "detector", "pixel", "calibracao"],
         criticidade="medio"),

    dict(patrimonio="RX-001", aberto_por="Lucia Mendes", setor_reportador="Radiologia",
         dias_atras=310, horas_resolucao=2,
         descricao="Cabeçote do raio-x não gira. Sistema de angulação travado. Impossível realizar tomadas em diferentes incidências.",
         resolucao="Mecanismo de angulação com oxidação no eixo e falta de lubrificação. Limpeza e lubrificação com graxa NLGI-2. Ajuste do freio eletromagnético. Movimentação suave em toda amplitude (0-90°).",
         tags=["raio-x", "cabecote", "angulacao", "lubrificacao", "mecanismo"],
         criticidade="baixo"),

    # ── OXÍMETRO DE PULSO ────────────────────────────────
    dict(patrimonio="OP-001", aberto_por="Sandra Costa", setor_reportador="Enfermaria",
         dias_atras=470, horas_resolucao=1,
         descricao="Oxímetro não lê SpO2. Display mostra --- mesmo com sensor posicionado corretamente. Paciente com quadro respiratório.",
         resolucao="Sensor digital de dedo com cabo rompido internamente (flexão repetida). Substituição do sensor reutilizável (NN-SENS-DIG). Leitura estável em 3 pacientes de teste.",
         tags=["oximetro", "spo2", "sensor", "cabo", "enfermaria"],
         criticidade="alto"),

    dict(patrimonio="OP-001", aberto_por="Paulo Ribeiro", setor_reportador="Enfermaria",
         dias_atras=390, horas_resolucao=2,
         descricao="Leituras de SpO2 com variação de até 8% em relação a oxímetro padrão. Valores imprecisos podem mascarar hipóxia.",
         resolucao="Sensor LED com potência emissora degradada (desgaste após ~15.000h de uso). Substituição do sensor e recalibração com oxímetro de referência certificado. Diferença < 1% após calibração.",
         tags=["oximetro", "spo2", "imprecisao", "calibracao", "led", "sensor"],
         criticidade="alto"),

    dict(patrimonio="OP-001", aberto_por="Fernanda Lima", setor_reportador="Enfermaria",
         dias_atras=280, horas_resolucao=1,
         descricao="Alarme de SpO2 baixo disparando constantemente em pacientes com saturação normal (> 95%).",
         resolucao="Limiar de alarme configurado erroneamente para 97% (padrão adulto = 90%). Reconfiguração do limiar para 90%. Orientação da equipe sobre configuração correta por setor.",
         tags=["oximetro", "alarme", "configuracao", "limiar", "spo2"],
         criticidade="baixo"),

    # ── RESPIRADOR DE TRANSPORTE ─────────────────────────
    dict(patrimonio="RS-001", aberto_por="Carlos Lima", setor_reportador="UTI",
         dias_atras=430, horas_resolucao=3,
         descricao="Respirador de transporte com vazamento audível no circuito do paciente. Pressão não mantida. Risco em transporte para tomografia.",
         resolucao="Vedante do Y-piece e conector de expiração com ressecamento. Substituição do kit de vedantes (DR-VED-OXY). Teste de estanqueidade: pressão de 40 cmH2O mantida por 30s sem variação.",
         tags=["respirador", "vazamento", "vedante", "circuito", "transporte"],
         criticidade="critico"),

    dict(patrimonio="RS-001", aberto_por="Ana Ferreira", setor_reportador="UTI",
         dias_atras=350, horas_resolucao=2,
         descricao="Alarme de 'BAIXA PRESSÃO DE OXIGÊNIO' mesmo com cilindro cheio. Pressurômetro do cilindro indica 150 bar.",
         resolucao="Regulador de pressão interno com diafragma desgastado reduzindo pressão de trabalho para abaixo do limiar. Substituição do regulador (DR-REG-300). Pressão de trabalho restaurada: 3,5 bar. Alarme resolvido.",
         tags=["respirador", "alarme", "pressao", "oxigenio", "regulador", "diafragma"],
         criticidade="critico"),

    dict(patrimonio="RS-001", aberto_por="Roberto Alves", setor_reportador="UTI",
         dias_atras=240, horas_resolucao=1,
         descricao="Display do respirador de transporte apagado. Modo de ventilação mantido (audível) mas sem visualização de parâmetros.",
         resolucao="Conector do display com falso contato por vibração durante transporte. Reaperto do conector e fixação com fita reforçada. Display estável. Recomendada verificação pré-transporte do conector.",
         tags=["respirador", "display", "conector", "vibração", "transporte"],
         criticidade="alto"),

    # ── PROBLEMAS ELÉTRICOS (vários equipamentos) ────────
    dict(patrimonio="MM-001", aberto_por="José Oliveira", setor_reportador="UTI",
         dias_atras=160, horas_resolucao=2,
         descricao="Monitor desliga sozinho após 5-10 minutos de uso. Sem mensagem de erro. Reinicia normalmente.",
         resolucao="Fonte de alimentação interna com capacitor de filtro seco causando instabilidade de tensão. Substituição dos capacitores eletrolíticos da fonte (kit PH-CAP-PSU). Teste de 8h contínuas sem desligamento.",
         tags=["monitor", "desliga", "fonte-alimentacao", "capacitor", "instabilidade"],
         criticidade="alto"),

    dict(patrimonio="VM-002", aberto_por="Maria Silva", setor_reportador="UTI",
         dias_atras=130, horas_resolucao=3,
         descricao="Ventilador com cheiro de queimado e micro-interruptor térmico disparado. Equipamento desligou automaticamente.",
         resolucao="Filtro de ar entupido causando superaquecimento do motor. Limpeza completa do filtro e ductos de ventilação. Substituição do filtro (HM-FIL-001). Reset do micro-interruptor térmico. Temperatura interna normalizada.",
         tags=["ventilador", "superaquecimento", "filtro", "temperatura", "motor"],
         criticidade="critico"),

    dict(patrimonio="BI-001", aberto_por="Paula Gomes", setor_reportador="UTI",
         dias_atras=100, horas_resolucao=1,
         descricao="Bomba de infusão com display apagando ao menor toque. Conexão precária.",
         resolucao="Parafuso de fixação do módulo de display solto por vibração. Reaperto com torquímetro (0,4 Nm). Teste de 2h sem reincidência. Verificar fixação em manutenções preventivas.",
         tags=["bomba-infusao", "display", "fixacao", "parafuso", "vibracao"],
         criticidade="medio"),

    # ── PROBLEMAS DE LIMPEZA / CONTAMINAÇÃO ──────────────
    dict(patrimonio="AC-001", aberto_por="Sandra Costa", setor_reportador="Centro Cirúrgico",
         dias_atras=190, horas_resolucao=5,
         descricao="Autoclave com odor forte e resíduo escuro nas paredes internas da câmara. Ciclos de esterilização potencialmente comprometidos.",
         resolucao="Depósito de carvão e gordura carbonizada por material cirúrgico orgânico inadequadamente pré-lavado. Limpeza química com produto específico (Endozyme x3 ciclos). Polimento das paredes com palha de aço inoxidável. Validação com indicadores biológicos: negativo para esporos.",
         tags=["autoclave", "limpeza", "contaminacao", "residuo", "validacao-biologica"],
         criticidade="alto"),

    dict(patrimonio="MM-002", aberto_por="Lucia Mendes", setor_reportador="Emergência",
         dias_atras=140, horas_resolucao=2,
         descricao="Monitor com teclas grudadas e resposta inconsistente após derramamento de soro fisiológico.",
         resolucao="Infiltração de solução salina no teclado de membrana. Desmontagem, limpeza com álcool isopropílico e ar comprimido. Secagem em estufa 40°C por 2h. Todas as teclas respondendo normalmente. Selado novamente com fita selante.",
         tags=["monitor", "teclado", "limpeza", "infiltracao", "soro"],
         criticidade="medio"),

    dict(patrimonio="BI-002", aberto_por="Carlos Lima", setor_reportador="Maternidade",
         dias_atras=110, horas_resolucao=1,
         descricao="Bomba com slot de equipo travado por resíduo de medicação solidificada (nutrição parenteral).",
         resolucao="Remoção do resíduo sólido com espátula plástica e limpeza enzimática. Mecanismo de clamp liberado. Lubrificação suave das guias. Verificar limpeza diária do slot após uso com nutrição parenteral.",
         tags=["bomba-infusao", "limpeza", "residuo", "nutricao-parenteral", "clamp"],
         criticidade="medio"),

    # ── PREVENTIVAS ENCONTRANDO PROBLEMAS ────────────────
    dict(patrimonio="VM-001", aberto_por="Sistema", setor_reportador="UTI",
         dias_atras=420, horas_resolucao=3,
         descricao="Manutenção preventiva de 15 dias. Verificação de rotina revelou sensor de fluxo com leitura 15% abaixo do calibrado.",
         resolucao="Sensor de fluxo recalibrado com fluxômetro padrão certificado. Todos os parâmetros dentro dos limites. Circuito do paciente substituído (prazo vencido). Filtro bacteriano trocado. Equipamento aprovado para uso.",
         tags=["ventilador", "preventiva", "calibracao", "sensor-fluxo", "filtro"],
         criticidade="medio"),

    dict(patrimonio="BI-001", aberto_por="Sistema", setor_reportador="UTI",
         dias_atras=360, horas_resolucao=2,
         descricao="Manutenção preventiva. Sensor de oclusão com calibração desviada 8% do limiar nominal.",
         resolucao="Recalibração do sensor de oclusão (limiar: 150 mmHg ± 5%). Limpeza interna. Bateria verificada: 78% da capacidade nominal. Lubrificação do mecanismo de clamp. Todos os alarmes testados e funcionais.",
         tags=["bomba-infusao", "preventiva", "calibracao", "sensor-oclusao", "manutencao"],
         criticidade="baixo"),

    dict(patrimonio="DF-001", aberto_por="Sistema", setor_reportador="Emergência",
         dias_atras=300, horas_resolucao=2,
         descricao="Teste semanal obrigatório do desfibrilador revelou carga 12% abaixo do selecionado (200J entregues vs 225J selecionados).",
         resolucao="Calibração de energia realizada (modo serviço, código ZL-SVC-001). Capacitor principal testado: capacitância dentro da tolerância. Problema era descalibração do módulo de medição de energia. Aprovado após calibração.",
         tags=["desfibrilador", "calibracao", "energia", "capacitor", "teste-semanal"],
         criticidade="critico"),

    dict(patrimonio="RS-001", aberto_por="Sistema", setor_reportador="UTI",
         dias_atras=240, horas_resolucao=2,
         descricao="Manutenção preventiva. Teste de estanqueidade falhou: pressão cai de 40 para 32 cmH2O em 30s.",
         resolucao="Identificado microvazamento no conector de expiração. Substituição do O-ring (DR-OR-EXP). Reteste: pressão mantida em 40 cmH2O por 60s. Circuito aprovado.",
         tags=["respirador", "preventiva", "estanqueidade", "o-ring", "conector"],
         criticidade="medio"),

    # ── PROBLEMAS PÓS-QUEDA / IMPACTO ────────────────────
    dict(patrimonio="OP-001", aberto_por="Roberto Alves", setor_reportador="Enfermaria",
         dias_atras=170, horas_resolucao=2,
         descricao="Oxímetro caiu da mesa de cabeceira. Display com trinca mas funcionando. Leitura imprecisa após queda.",
         resolucao="Display com trinca no vidro de proteção mas LCD funcional. Substituição do vidro protetor (NN-VID-001). Recalibração do sensor (diferença < 1% após calibração). Carcaça verificada sem outros danos. Equipamento aprovado.",
         tags=["oximetro", "queda", "display", "calibracao", "impacto"],
         criticidade="medio"),

    dict(patrimonio="RX-001", aberto_por="Paula Gomes", setor_reportador="Radiologia",
         dias_atras=130, horas_resolucao=3,
         descricao="Raio-x portátil com roda dianteira quebrada após colisão com porta. Equipamento inclinado e instável.",
         resolucao="Conjunto de roda substituído (GE-ROD-001). Nivelamento do equipamento verificado (bolha de nível). Teste de estabilidade em superfície inclinada aprovado. Equipamento seguro para uso.",
         tags=["raio-x", "roda", "mecanico", "queda", "estabilidade"],
         criticidade="baixo"),

    # ── PROBLEMAS ELÉTRICOS NA REDE ──────────────────────
    dict(patrimonio="MM-001", aberto_por="Carlos Lima", setor_reportador="UTI",
         dias_atras=230, horas_resolucao=4,
         descricao="Após queda de energia no hospital, monitor não liga mais. Fonte aparentemente danificada pela transiente de tensão.",
         resolucao="Fusível de proteção da fonte queimado por transiente de retorno de energia. Substituição do fusível (PH-FUS-3A) e do varistor de proteção (MOV 275V). Monitor funcionando normalmente. Recomendado uso de nobreak para este equipamento.",
         tags=["monitor", "fonte-alimentacao", "fusivel", "transiente", "queda-energia", "nobreak"],
         criticidade="critico"),

    dict(patrimonio="VM-002", aberto_por="Ana Ferreira", setor_reportador="UTI",
         dias_atras=195, horas_resolucao=2,
         descricao="Ventilador em operação normal mas com alarmes elétricos intermitentes. Medição de corrente de fuga acima de 100µA.",
         resolucao="Aterramento do ponto de instalação com resistência de 8Ω (máx: 0,2Ω). Solicitada correção da rede elétrica pela engenharia predial. Equipamento temporariamente realocado para tomada com aterramento correto.",
         tags=["ventilador", "aterramento", "corrente-fuga", "eletrico", "seguranca"],
         criticidade="alto"),

    # ── PROBLEMAS DE SOFTWARE / CONFIGURAÇÃO ─────────────
    dict(patrimonio="BI-003", aberto_por="Fernanda Lima", setor_reportador="UTI",
         dias_atras=210, horas_resolucao=1,
         descricao="Biblioteca de medicamentos da bomba mostrando concentrações desatualizadas. Risco de subdosagem/superdosagem.",
         resolucao="Atualização da biblioteca de medicamentos para versão 2024.12 via software Alaris Service. Verificação de 50 protocolos de maior uso. Teste de segurança de doses realizado com farmacêutico. Aprovado.",
         tags=["bomba-infusao", "software", "biblioteca", "medicamento", "atualizacao"],
         criticidade="alto"),

    dict(patrimonio="MM-002", aberto_por="José Oliveira", setor_reportador="Emergência",
         dias_atras=160, horas_resolucao=1,
         descricao="Monitor com data e hora erradas após troca de bateria. Log de eventos comprometido com timestamps incorretos.",
         resolucao="Bateria do RTC (relógio interno) descarregada após troca de bateria principal. Substituição da bateria de botão CR2032. Configuração de data/hora e sincronização com servidor NTP do hospital.",
         tags=["monitor", "data-hora", "rtc", "bateria-botao", "log"],
         criticidade="baixo"),

    # ── CASOS COM WIKILINKS CRUZADOS (relacionados) ──────
    dict(patrimonio="BI-001", aberto_por="Maria Silva", setor_reportador="UTI",
         dias_atras=85, horas_resolucao=2,
         descricao="Terceiro episódio de alarme E05 na BI-001 em 30 dias. Sensor trocado há 6 semanas ainda apresentando falha.",
         resolucao="Investigado histórico (CHM relacionados). Constatado que o modelo de equipo sendo utilizado (genérico) é incompatível com o sensor Fresenius. Padronização do equipo descartável para marca Fresenius original. Sem reincidências após padronização.",
         tags=["bomba-infusao", "e05", "reincidencia", "equipo-compativel", "padronizacao"],
         criticidade="alto"),

    dict(patrimonio="VM-001", aberto_por="Carlos Lima", setor_reportador="UTI",
         dias_atras=70, horas_resolucao=3,
         descricao="Alarme de FiO2 baixo recorrente. Quarto episódio em 2 meses. Sensor trocado anteriormente.",
         resolucao="Investigado: constatado que cilindros de O2 da central apresentam umidade acima do especificado, degradando os sensores prematuramente. Instalado filtro de umidade na entrada de gás (DR-FIL-O2). Problema estrutural reportado à engenharia clínica.",
         tags=["ventilador", "fio2", "sensor-oxigenio", "umidade", "cilindro", "filtro"],
         criticidade="critico"),

    dict(patrimonio="AC-001", aberto_por="Paula Gomes", setor_reportador="Centro Cirúrgico",
         dias_atras=55, horas_resolucao=2,
         descricao="Autoclave não passando no teste de Bowie-Dick. Vapor com qualidade insuficiente para esterilização.",
         resolucao="Gerador de vapor com incrustação de calcário reduzindo eficiência. Descalcificação química com ácido cítrico 5% por 4h. Filtro de água instalado na entrada (CR-FIL-H2O). Teste Bowie-Dick aprovado.",
         tags=["autoclave", "bowie-dick", "vapor", "calcario", "descalcificacao"],
         criticidade="alto"),

    dict(patrimonio="DF-001", aberto_por="Roberto Alves", setor_reportador="Emergência",
         dias_atras=40, horas_resolucao=4,
         descricao="Desfibrilador com erro E-07 novamente. Mesmo erro do chamado há 1 ano. Capacitor recém trocado.",
         resolucao="Investigado com fabricante: lote de capacitores ZL-CAP-360J (série 2024-A) com defeito de fabricação. Substituição pelo lote 2024-C (sem defeito). Reportado recall ao distribuidor. 3 equipamentos do hospital afetados verificados.",
         tags=["desfibrilador", "e07", "capacitor", "recall", "fabricante", "lote"],
         criticidade="critico"),

    dict(patrimonio="RX-001", aberto_por="Lucia Mendes", setor_reportador="Radiologia",
         dias_atras=25, horas_resolucao=3,
         descricao="Imagem com artefatos crescente. Mesmo problema de 8 meses atrás, mas mais intenso.",
         resolucao="Detector com novo conjunto de pixels mortos em 3 linhas horizontais. Recalibração via software (92% dos pixels recuperados). Recomendada substituição do painel detector em próxima janela de manutenção. Orçamento solicitado.",
         tags=["raio-x", "detector", "pixel", "artefato", "degradacao"],
         criticidade="medio"),

]

# ─────────────────────────────────────────────────────────
#  GERAR .MD DE CHAMADO RESOLVIDO
# ─────────────────────────────────────────────────────────
def gerar_md(chamado_id: int, c: dict, eq: Equipamento) -> str:
    criado_em = (datetime.utcnow() - timedelta(days=c["dias_atras"])).isoformat(timespec='seconds')
    resolvido_em = (datetime.utcnow() - timedelta(days=c["dias_atras"]) + timedelta(hours=c["horas_resolucao"])).isoformat(timespec='seconds')
    ano = datetime.utcnow().year
    chm_id = f"CHM-{ano}-{chamado_id:04d}"
    tags_yaml = json.dumps(c["tags"], ensure_ascii=False)
    tags_inline = ", ".join(f"`{t}`" for t in c["tags"])

    return f"""---
id: {chm_id}
titulo: "{eq.descricao} — {c['descricao'][:60].rstrip()}"
tags: {tags_yaml}
patrimonio: {eq.patrimonio}
setor: {eq.setor}
criticidade: {c['criticidade']}
status: resolvido
aberto_por: {c['aberto_por']}
setor_reportador: {c['setor_reportador']}
criado_em: {criado_em}
resolvido_em: {resolvido_em}
---

## Problema

**Equipamento:** {eq.descricao} ({eq.patrimonio}) — {eq.localizacao}

{c['descricao']}

## Resolução

{c['resolucao']}

**Técnico responsável:** {c['aberto_por']}
**Tempo de atendimento:** {c['horas_resolucao']}h
**Resolvido em:** {resolvido_em}

## Tags

{tags_inline}
"""


async def indexar_arquivo(md_path: str, metadata: dict) -> bool:
    try:
        from app.services.rag_service import rag_service
        await rag_service.indexar_documento(md_path, metadata)
        return True
    except Exception as e:
        print(f"    [!] Erro ao indexar {Path(md_path).name}: {e}")
        return False


def seed():
    knowledge_root = Path(KNOWLEDGE_DIR)
    (knowledge_root / "chamados").mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        # ── Equipamentos ─────────────────────────────
        print("=== Equipamentos ===")
        eq_map: dict[str, Equipamento] = {}
        for data in EQUIPAMENTOS:
            existing = session.exec(
                select(Equipamento).where(Equipamento.patrimonio == data["patrimonio"])
            ).first()
            if not existing:
                eq = Equipamento(**data)
                session.add(eq)
                session.flush()
                print(f"  [+] {eq.patrimonio} — {eq.descricao}")
                eq_map[eq.patrimonio] = eq
            else:
                print(f"  [=] {existing.patrimonio} já existe")
                eq_map[existing.patrimonio] = existing
        session.commit()

        # ── Chamados + .md ────────────────────────────
        print(f"\n=== Chamados ({len(CHAMADOS)} registros) ===")
        arquivos_para_indexar = []
        criados = 0

        for c_data in CHAMADOS:
            pat = c_data["patrimonio"]
            eq = eq_map.get(pat)
            if not eq:
                print(f"  [!] Equipamento {pat} não encontrado")
                continue

            # Verifica se já existe chamado com mesma descrição
            existing = session.exec(
                select(Chamado).where(
                    Chamado.equipamento_id == eq.id,
                    Chamado.descricao == c_data["descricao"]
                )
            ).first()

            if existing:
                print(f"  [=] {pat} — já existe (id={existing.id})")
                if existing.md_path:
                    meta = {"titulo": f"CHM-{ANO}-{existing.id:04d} {eq.descricao}",
                            "tipo": "chamado_resolvido", "arquivo_path": existing.md_path}
                    arquivos_para_indexar.append((existing.md_path, meta))
                continue

            criado_em = datetime.utcnow() - timedelta(days=c_data["dias_atras"])
            fechado_em = criado_em + timedelta(hours=c_data["horas_resolucao"])

            chamado = Chamado(
                equipamento_id=eq.id,
                tipo="corretivo",
                aberto_por=c_data["aberto_por"],
                setor_reportador=c_data["setor_reportador"],
                descricao=c_data["descricao"],
                criticidade_sugerida=c_data["criticidade"],
                criticidade_confirmada=c_data["criticidade"],
                resolucao=c_data["resolucao"],
                status="resolvido",
                validado=True,
                validado_por="seed_volume",
                validado_em=fechado_em,
                criado_em=criado_em,
                fechado_em=fechado_em,
            )
            session.add(chamado)
            session.flush()

            # Gera .md
            md_conteudo = gerar_md(chamado.id, c_data, eq)
            md_path = knowledge_root / "chamados" / f"CHM-{ANO}-{chamado.id:04d}.md"
            md_path.write_text(md_conteudo, encoding="utf-8")

            chamado.md_path = str(md_path)
            session.add(chamado)

            # Registra FonteConhecimento
            fonte_existente = session.exec(
                select(FonteConhecimento).where(FonteConhecimento.arquivo_path == str(md_path))
            ).first()
            if not fonte_existente:
                fonte = FonteConhecimento(
                    titulo=f"CHM-{ANO}-{chamado.id:04d} {eq.descricao}",
                    tipo="chamado_resolvido",
                    arquivo_path=str(md_path),
                    tags=json.dumps(c_data["tags"], ensure_ascii=False),
                )
                session.add(fonte)

            meta = {
                "titulo": f"CHM-{ANO}-{chamado.id:04d} {eq.descricao}",
                "tipo": "chamado_resolvido",
                "patrimonio": pat,
                "setor": c_data["setor_reportador"],
                "arquivo_path": str(md_path),
            }
            arquivos_para_indexar.append((str(md_path), meta))
            criados += 1
            print(f"  [+] CHM-{ANO}-{chamado.id:04d} — {pat}: {c_data['descricao'][:55]}…")

        session.commit()
        print(f"\n  {criados} chamados criados, {len(CHAMADOS) - criados} já existiam.")

    # ── ChromaDB ─────────────────────────────────────────
    print(f"\n=== ChromaDB ({len(arquivos_para_indexar)} arquivos) ===")
    print("  (requer Ollama com nomic-embed-text rodando)")

    async def indexar_tudo():
        ok = 0
        for caminho, meta in arquivos_para_indexar:
            sucesso = await indexar_arquivo(caminho, meta)
            if sucesso:
                ok += 1
                print(f"  [✓] {Path(caminho).name}")
        print(f"\n  {ok}/{len(arquivos_para_indexar)} arquivos indexados no ChromaDB.")

    try:
        asyncio.run(indexar_tudo())
    except Exception as e:
        print(f"  [!] {e}")
        print("      Rode com Ollama ativo para indexar no ChromaDB.")

    print("\n=== Seed de volume concluído! ===")
    print(f"  {len(CHAMADOS)} chamados hospitalares gerados")
    print(f"  Testе o RAG no admin: http://localhost:8000/static/admin.html")
    print(f"  Pergunte: 'bomba de infusão com alarme E05' → deve retornar 4+ casos")


if __name__ == "__main__":
    print("3Notes.AI — Seed de volume (50 chamados hospitalares)\n")
    seed()
