# Protocolo de Manutencao Corretiva - Hospital Regional Norte
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
