---
titulo: "Boas Práticas — Reporter (Abertura de Chamados)"
tipo: protocolo
tags: ["reporter", "boas-praticas", "abertura", "chamado", "descricao", "patrimonio"]
versao: 1.0
vigencia: 2026
---

# Boas Práticas — Reporter 3Notes.AI

O Reporter é a porta de entrada do conhecimento. Uma nota de abertura bem escrita
acelera o atendimento e alimenta o RAG com informações de qualidade.

---

## 1. Identifique o equipamento corretamente

Sempre informe o número de patrimônio antes de descrever o problema.
O patrimônio é a etiqueta fixada no equipamento (ex: VM-001, BI-005, DF-004).

**Bom:** "Bomba de infusão BI-001, UTI Leito 7, alarme E05."
**Ruim:** "A bomba do leito está com alarme."

Sem patrimônio, a IA não consegue buscar histórico do equipamento específico.

---

## 2. Descreva o problema com sintomas, não hipóteses

Relate o que você **vê, ouve e lê** no display. Não tente diagnosticar.

**Bom:**
- "Display mostra código E-07. Equipamento não carrega ao pressionar o botão."
- "Ruído de raspagem vindo do módulo de fluxo. Audível a 1 metro."
- "SpO2 aparece como --- mesmo com sensor posicionado corretamente."

**Ruim:**
- "Acho que o capacitor queimou."
- "Parece problema elétrico."

Os códigos de erro (E05, E07, E12, ALTO PEEP, APNEIA) são cruciais — inclua sempre.

---

## 3. Informe o contexto clínico quando crítico

Se o equipamento está em uso direto com paciente, diga explicitamente.
Isso influencia a criticidade sugerida pela IA.

**Exemplos:**
- "Paciente em sedação contínua dependente da bomba."
- "Ventilador em uso — paciente sem respiração espontânea."
- "Equipamento reserva, sem paciente no momento."

---

## 4. Use a criticidade sugerida como ponto de partida

A IA sugere uma criticidade com base na descrição. Você pode ajustá-la.
Guia rápido:

| Criticidade | Quando usar |
|---|---|
| **Crítico** | Equipamento em uso com paciente, sem substituto disponível |
| **Alto** | Equipamento importante com substituto disponível |
| **Médio** | Equipamento de suporte com baixo impacto imediato |
| **Baixo** | Equipamento auxiliar, problema cosmético ou administrativo |

---

## 5. Revise a prévia do arquivo .md antes de confirmar

A tela de prévia mostra exatamente como a nota será salva.
Verifique:
- Título está descritivo (não genérico)
- Tags fazem sentido para o problema relatado
- Patrimônio e setor estão corretos

A nota gerada alimenta diretamente a Memória da IA após validação do Master.
Uma nota ruim = conhecimento ruim = sugestões erradas para o próximo técnico.

---

## 6. Use o Copiloto para dúvidas antes de enviar

O copiloto (botão 🤖 no canto superior da tela) acessa a base histórica.
Antes de enviar, você pode perguntar:

- "Já houve chamados similares na bomba BI-001?"
- "Qual a criticidade correta para ventilador com alarme de pressão?"
- "Quais informações o técnico vai precisar para resolver isso?"

---

## Por que isso importa

Cada chamado bem documentado vira uma nota .md no sistema.
Quando o próximo técnico enfrentar o mesmo problema, a IA vai encontrar
essa nota e sugerir a solução que funcionou — economizando horas de diagnóstico.

O conhecimento não morre mais quando um técnico sai do hospital.
