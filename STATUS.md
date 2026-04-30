# 3Notes.AI — Status do Projeto

**Última atualização:** 2026-04-23
**Autor:** Luiz Filipe Pereira Nunes
**Hackathon:** Gemma 4 Good (Kaggle / Google)

---

## O que é

3Notes.AI é um sistema de gestão de conhecimento operacional para setores com equipamentos críticos. A narrativa central é uma tríade de três tipos de nota:

```
         [Master — Nota 3]
              /       \
     Curadoria      Conhecimento
          /               \
[Reporter — Nota 1] — [Dashboard — Nota 2]
  Abertura do chamado   Resolução documentada
```

- **Nota 1 (Reporter):** o funcionário abre o chamado, descreve o problema. A IA sugere criticidade. Gera um `.md`.
- **Nota 2 (Dashboard):** o técnico resolve e documenta causa raiz + procedimento. Gera outro `.md`.
- **Nota 3 (Master):** o administrador valida o que entra na memória da IA. Curadoria de protocolos e manuais.

Os três arquivos Markdown formam clusters interconectados via wikilinks `[[CHM-YYYY-NNNN]]` e tags — estrutura análoga ao Obsidian, mas gerada automaticamente pelo fluxo de trabalho real.

---

## Como se comporta

Funciona como **NotebookLM do Google**, mas:
- 100% local (sem internet, sem nuvem, sem exposição de dados)
- Gera a base de conhecimento automaticamente a partir das operações (chamados e resoluções)
- O administrador (Master) é o controle de qualidade do que a IA aprende

Funciona como **Obsidian**, mas:
- Os arquivos `.md` são criados pelo sistema, não pelo usuário
- Os wikilinks são gerados automaticamente ao resolver chamados (RAG + markdown)
- O grafo de conhecimento é gerado a partir dos dados reais

---

## Hardware em uso (referência)

| Componente | Especificação |
|---|---|
| Máquina | Dell Optiplex 3080 |
| CPU | Intel Core i5-10500 |
| RAM | 16 GB |
| GPU | Nenhuma (CPU only) |
| OS | Ubuntu 24.04.4 LTS |
| Modelo LLM | `gemma4:e2b` (2B parâmetros, 7.2 GB na RAM) |
| Embed model | `nomic-embed-text` (768 dimensões) |
| Vector DB | ChromaDB (persistente, HNSW cosine) |

> O modelo `gemma4:27b` (9.6 GB) trava nessa máquina — `gemma4:e2b` é o limite prático.
> Em servidores com mais RAM ou GPU, qualquer modelo maior funciona sem modificar o código.

---

## Stack técnica

```
FastAPI (Python)
├── SQLModel + SQLite          — banco relacional (chamados, equipamentos)
├── ChromaDB (persistente)     — vector store para RAG
├── Ollama (local)             — LLM + embeddings
│   ├── gemma4:e2b             — chat / geração
│   └── nomic-embed-text       — embeddings 768-dim
└── Markdown files (.md)       — source of truth do conhecimento
    ├── knowledge/chamados/    — chamados resolvidos
    ├── knowledge/manuais/     — manuais técnicos
    └── knowledge/protocolos/  — boas práticas e protocolos
```

---

## Estado atual da base de conhecimento

| Tipo | Quantidade |
|---|---|
| Chamados no SQL | 63 |
| Chamados validados (no RAG) | 53 |
| Equipamentos cadastrados | 12 |
| Protocolos indexados | 3 |
| Manuais indexados | 2 |
| Total de chunks no ChromaDB | ~67 |

**Equipamentos simulados:**
VM-001, VM-002 (Ventiladores), MM-001, MM-002 (Monitores Multiparâmetros),
BI-001, BI-002, BI-003 (Bombas de Infusão), AC-001 (Autoclave),
DF-001 (Desfibrilador), RX-001 (Raio-X Portátil), OP-001 (Oxímetro), RS-001 (Ressuscitador)

---

## Páginas / Rotas

| Rota | Descrição |
|---|---|
| `/` | Redireciona para o Reporter |
| `/static/reporter.html` | App 1 — Reporter (funcionários) |
| `/static/dashboard.html` | App 2 — Dashboard (técnicos) |
| `/static/admin.html` | App 3 — Master (administrador) |
| `/docs` | Swagger UI da API |
| `/health` | Status do servidor e modelo ativo |

---

## API Principal

```
POST /ai/chat              — chat não-streaming (intake flow)
POST /ai/chat/stream       — SSE streaming (copiloto)
POST /ai/confirmar-chamado — cria chamado + gera .md + indexa

GET  /api/chamados         — lista chamados
GET  /api/equipamentos     — lista equipamentos
GET  /api/knowledge/fontes — fontes curadas indexadas
GET  /api/knowledge/buscar — busca semântica no ChromaDB
GET  /api/knowledge/grafo  — dados do grafo (nós + arestas)
POST /api/knowledge/upload — indexa novo documento
GET  /api/metricas         — métricas do dashboard
```

---

## Deferred Embedding (arquitetura chave)

```
Reporter abre chamado
       ↓
Salvo em SQLite ✓  +  .md salvo em disco ✓  +  ChromaDB ✗
       ↓
Master valida (aprova qualidade)
       ↓
POST /api/chamados/{id}/validar
       ↓
Chunk → embed (nomic-embed-text) → ChromaDB ✓
       ↓
RAG ativo: próximas perguntas ao copiloto retornam esse contexto
```

O Master é o controle de qualidade do que a IA aprende.
Chamado mal descrito → fica fora do RAG (permanece no SQL, pode ser resolvido normalmente).

---

## As 3 Notas — narrativa do nome

O nome 3Notes reflete a arquitetura de conhecimento:

1. **Nota de Abertura** — documenta *o que aconteceu*
2. **Nota de Resolução** — documenta *o que funcionou*
3. **Nota de Conhecimento** — documenta *o que deve ser feito*

Juntas, formam uma base de conhecimento que aprende com cada ocorrência e nunca perde o saber acumulado — mesmo com rotatividade de equipe.

---

## Para rodar

```bash
cd 3notes
source .venv/bin/activate
python scripts/seed_demo.py       # dados base (12 eq + 10 chamados)
python scripts/seed_volume.py     # volume realista (53 chamados históricos)
uvicorn app.main:app --reload
# acesse http://localhost:8000
```

**Pré-requisitos:** Ollama rodando com `gemma4:e2b` e `nomic-embed-text` instalados.

```bash
ollama pull gemma4:e2b
ollama pull nomic-embed-text
```
