---
titulo: "Boas Práticas — Dashboard Técnico (Atendimento e Resolução)"
tipo: protocolo
tags: ["dashboard", "tecnico", "boas-praticas", "resolucao", "atendimento", "sla", "wikilink"]
versao: 1.0
vigencia: 2026
---

# Boas Práticas — Dashboard Técnico 3Notes.AI

O Dashboard é onde o conhecimento se torna ação. Uma resolução bem documentada
gera a nota mais valiosa do sistema: o registro do que funcionou.

---

## 1. Atenda por ordem de criticidade, não por ordem de chegada

A fila é ordenada automaticamente: Crítico → Alto → Médio → Baixo.
Não reorganize mentalmente com base em quem pediu primeiro.

**SLA de referência:**
| Criticidade | Tempo máximo |
|---|---|
| Crítico | 2 horas |
| Alto | 8 horas |
| Médio | 24 horas |
| Baixo | 72 horas |

O indicador de tempo no card fica vermelho quando o SLA crítico foi ultrapassado.

---

## 2. Use o Copiloto antes de ir ao equipamento

Abra o chamado no painel lateral e pergunte ao copiloto (🤖):

- "Quais as causas mais comuns desse alarme nesse equipamento?"
- "Esse erro já ocorreu antes? Como foi resolvido?"
- "Quais peças podem ser necessárias?"

O copiloto lê a base histórica e retorna casos similares resolvidos com as soluções
que funcionaram. Isso evita tentativa e erro e reduz o tempo de diagnóstico.

---

## 3. Mude o status para "Em andamento" antes de sair

Clique em **"Iniciar atendimento"** no painel do chamado assim que assumir o caso.
Isso:
- Informa a equipe que o chamado está sendo tratado
- Registra no histórico quem assumiu e quando
- Evita que outro técnico vá até o mesmo equipamento

---

## 4. Confirme a criticidade se diferir do sugerido

A criticidade sugerida pelo funcionário pode não corresponder à realidade técnica.
Use o seletor no painel para confirmar ou corrigir antes de resolver.

Exemplos de ajuste comum:
- Funcionário marcou "crítico" mas há substituto disponível → corrigir para "alto"
- Funcionário marcou "médio" mas paciente dependente → corrigir para "crítico"

---

## 5. Documente a resolução com causa raiz + procedimento + peças

A nota de resolução é o ativo mais valioso do sistema.
O que você escrever aqui vai ajudar o próximo técnico que enfrentar o mesmo problema.

**Estrutura recomendada:**

```
Causa raiz: [o que causou o problema]
Procedimento: [o que foi feito, passo a passo]
Peças substituídas: [código + lote se aplicável]
Observação: [o que observar para prevenir reincidência]
```

**Bom:**
"Sensor de oclusão obstruído por resíduo de nutrição parenteral cristalizada.
Limpeza com solução enzimática e recalibração (150 mmHg). Equipo descartável
substituído. Verificar limpeza diária do slot após uso com NP."

**Ruim:**
"Limpei e funcionou."

---

## 6. Os wikilinks gerados são dados — use-os

Ao registrar a resolução, o sistema automaticamente busca chamados relacionados
na base e gera links [[CHM-YYYY-NNNN]] na nota .md.

Esses links indicam equipamentos com problemas similares ou que podem ser
afetados pela mesma causa raiz. Clique nos links no painel para ver os casos
relacionados — podem revelar padrões de falha sistêmica.

---

## 7. Quando acionar o Master

Acione o Master (admin.html) quando:
- O chamado exigir ajuste em dados incorretos antes de validar
- O equipamento não constar no cadastro
- A resolução envolver recall de fornecedor ou problema sistêmico
- O chamado tiver impacto em mais de um setor simultaneamente

---

## Por que a nota de resolução importa

Cada resolução documentada = uma nota .md salva na Memória da IA.
A IA aprende especificamente com o que funcionou no seu hospital,
com os seus equipamentos, no seu contexto clínico.

Em 6 meses de uso, o copiloto já sabe que a BI-001 tem problema recorrente
de sensor E05 com equipo genérico, e vai recomendar a solução correta
antes mesmo de você chegar ao equipamento.
