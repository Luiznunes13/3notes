---
titulo: "Boas Práticas — Master (Validação e Curadoria da Memória)"
tipo: protocolo
tags: ["master", "validacao", "curadoria", "embedding", "chromadb", "qualidade", "boas-praticas"]
versao: 1.0
vigencia: 2026
---

# Boas Práticas — Master 3Notes.AI

O Master é o guardião da qualidade do conhecimento.
O que passa pela sua aprovação entra na Memória da IA e influencia todas as
respostas futuras do copiloto. Dados ruins = sugestões ruins.

---

## 1. Entenda o que é o Deferred Embedding

Quando um funcionário abre um chamado via Reporter:
1. O chamado é salvo no banco de dados ✓
2. O arquivo .md é salvo em disco ✓
3. **O chamado NÃO entra no ChromaDB ainda** ✗

Só após sua aprovação o dado é embeddado (indexado vetorialmente) e passa a
enriquecer o RAG. Isso protege a base de conhecimento de dados incorretos,
duplicados ou com informações clínicas erradas.

**Você é o controle de qualidade do que a IA aprende.**

---

## 2. Critérios de validação

Antes de clicar em "Validar e embedar", verifique:

**Dados obrigatórios corretos:**
- [ ] Patrimônio do equipamento identificado e existente no cadastro
- [ ] Setor reportador corresponde ao equipamento
- [ ] Nome de quem abriu o chamado preenchido
- [ ] Descrição do problema é específica (não genérica como "não funciona")

**Qualidade da descrição:**
- [ ] Contém sintomas observáveis (códigos de erro, sons, comportamento)
- [ ] Criticidade faz sentido para o contexto clínico descrito
- [ ] Não contém dados de paciente identificáveis (nome, prontuário)

**Se algo está errado:** use "Editar" antes de validar.
Corrija a descrição, o setor ou a criticidade — só então valide.

---

## 3. Quando rejeitar (não validar)

Não valide chamados que:
- São duplicatas de chamado já existente (mesmo equipamento, mesmo problema)
- Descrevem problemas em equipamentos inexistentes no hospital
- Contém informações clínicas sensíveis do paciente na descrição
- São testes ou registros de treinamento ("teste 123", "abc")
- Têm descrição tão vaga que não agrega conhecimento ("deu pau")

Chamados não validados permanecem no banco mas ficam fora do RAG.
Eles ainda aparecem no dashboard e podem ser resolvidos normalmente.

---

## 4. Curadoria da Memória — o que indexar além dos chamados

A seção **Memória da IA** permite adicionar documentos externos ao ChromaDB:

**Adicionar:**
- Manuais técnicos do fabricante (mesmo que em PDF)
- Protocolos de manutenção preventiva do hospital
- Laudos de calibração com as especificações dos instrumentos
- Boletins de segurança e recalls de equipamentos

**Não adicionar:**
- Documentos desatualizados (versão antiga substituída por nova)
- Arquivos escaneados sem OCR (texto não legível pela IA)
- Documentos com dados pessoais de pacientes ou funcionários
- Duplicatas de documentos já indexados

---

## 5. Teste o RAG regularmente

Use o painel de busca semântica para validar que a base está funcionando:

**Testes recomendados semanalmente:**
- Busque por um problema que você sabe que foi resolvido recentemente
- Verifique se a solução correta aparece nos primeiros resultados
- Teste com termos técnicos E com linguagem leiga (como um funcionário escreveria)

**Sinais de que a base precisa de atenção:**
- Busca retorna resultados irrelevantes para o termo pesquisado
- Chamados resolvidos há mais de 1 semana não aparecem (falha de indexação)
- Documentos antigos aparecem com mais relevância que os recentes

---

## 6. Gestão de equipamentos

Mantenha o cadastro de equipamentos atualizado:
- Adicione novos equipamentos antes de ativá-los clinicamente
- Atualize o setor quando houver remanejamento
- Marque como inativo equipamentos retirados de serviço
- Revise o intervalo de preventiva a cada contrato de manutenção

---

## As 3 Notas do 3Notes.AI

O nome do sistema reflete sua arquitetura de conhecimento:

**Nota 1 — Abertura (Reporter):**
O funcionário descreve o problema. A IA sugere criticidade e tags.
Esta nota documenta *o que aconteceu*.

**Nota 2 — Resolução (Dashboard):**
O técnico documenta a causa raiz e o procedimento.
Esta nota documenta *o que funcionou*.

**Nota 3 — Conhecimento (Master):**
Manuais, protocolos e documentos institucionais.
Esta nota documenta *o que deve ser feito*.

Juntas, as 3 notas formam uma base de conhecimento que aprende com cada
ocorrência e nunca perde o saber acumulado — mesmo com rotatividade de equipe.
