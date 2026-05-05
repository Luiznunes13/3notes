# 3Notes.AI — Intelligent Knowledge System for Hospital Maintenance

> **"Every resolved ticket makes the next one faster."**
>
> Gemma 4 Good Hackathon · Kaggle × Google DeepMind · [CC-BY 4.0](LICENSE)

---

## The Problem

Brazilian public hospitals have over **43,000 medical devices out of service** due to lack of maintenance management (source: CNES/Ministry of Health). Maintenance is managed with paper notebooks or spreadsheets — no history, no pattern recognition, no institutional memory.

Worse: **institutional knowledge disappears** with every shift change or staff departure. The technician who fixed that ventilator three times last year? When they leave, the hospital loses everything they learned.

---

## The Solution

**3Notes.AI** is a three-role knowledge management system for hospital maintenance, powered by RAG with Gemma 4. Every interaction generates a structured `.md` file that feeds the knowledge base — **the system learns and improves with every resolved ticket**, inspired by Google's NotebookLM and Obsidian's interconnected note philosophy.

### Why "3Notes"

```
        [Master — Note 3]
             /        \
      Curation       Knowledge
         /                \
[Reporter — Note 1] — [Dashboard — Note 2]
  "What happened"       "What worked"
```

| Note | Role | Documents |
|---|---|---|
| **Note 1 — Reporter** | Staff member describes the problem via AI chat | *What happened* |
| **Note 2 — Dashboard** | Technician documents root cause and resolution | *What worked* |
| **Note 3 — Master** | Admin validates knowledge and manages curated docs | *What should be done* |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         3Notes.AI                            │
│                                                              │
│  ┌─────────────┐   ┌──────────────────┐   ┌──────────────┐  │
│  │  App 1      │   │  App 2           │   │  App 3       │  │
│  │  Reporter   │   │  Dashboard       │   │  Master      │  │
│  │  (Mobile)   │   │  (Technician)    │   │  (Admin)     │  │
│  │             │   │                  │   │              │  │
│  │  Chat + .md │   │  Queue + Metrics │   │  Validation  │  │
│  │  generation │   │  RAG copilot     │   │  + Curation  │  │
│  └──────┬──────┘   └────────┬─────────┘   └──────┬───────┘  │
│         └─────── FastAPI REST API ────────────────┘           │
│                       │                                      │
│             ┌─────────┴─────────┐                            │
│             │  SQLite + .md     │  ChromaDB (HNSW cosine)    │
│             │  Knowledge Store  │  68 chunks · 1024-dim      │
│             └───────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

---

## How Gemma 4 is Used

Gemma 4 is the **central intelligence** of 3Notes.AI — not decorative:

| Function | How Gemma 4 is used |
|---|---|
| **Conversational intake** | Conducts structured chat to collect ticket data without forms |
| **RAG copilot** | Retrieves relevant `.md` context from ChromaDB before answering |
| **Source citation** | Cites previous cases as `[CHM-2026-0021]` or `[Document Name]` |
| **Title generation** | Creates concise, descriptive titles for each `.md` note |
| **Tag suggestion** | Suggests kebab-case PT tags for semantic indexing |
| **Criticality suggestion** | Proposes urgency level with explainable justification |

The system scales from `gemma4:e2b` (2B params, CPU-only) to `gemma4:27b` without any code changes — just update `THREENNOTES_MODEL` in `.env`.

---

## Key Design Decisions

### Deferred Embedding — The Quality Gate

```
Staff opens ticket
      ↓
SQLite ✓  +  .md saved to disk ✓  +  ChromaDB ✗
      ↓
Master validates (quality, relevance, no patient data)
      ↓
POST /api/chamados/{id}/validar
      ↓
Chunk → embed (qwen3-embedding:0.6b) → ChromaDB ✓
      ↓
RAG active: next copilot queries return this context
```

**The Master is the quality gate of what the AI learns.** A poorly described ticket stays out of the RAG — it remains in SQL and can be resolved normally, but does not contaminate the knowledge base.

### Cosine Distance Threshold — No Hallucination

Cosine distance threshold of **0.45** filters irrelevant chunks before injection:

```
"pump occlusion alarm"
        │
qwen3-embedding:0.6b (1024-dim, 32K context, multilingual)
        │
ChromaDB HNSW cosine search
        │
dist=0.215 → CHM-2026-0021 ✅  injected into context
dist=0.270 → CHM-2026-0004 ✅  injected into context
dist=0.571 → unrelated doc  ❌  discarded
```

Empirical calibration on PT-BR hospital queries found a natural gap: relevant chunks score 0.21–0.42, irrelevant ones 0.57–0.62. The threshold eliminates citation hallucination — the model only cites sources that genuinely exist and are semantically close.

### Graph Expansion via Wikilinks

After the initial vector search, the system follows `[[CHM-YYYY-NNNN]]` wikilinks embedded in retrieved `.md` files — a 2-hop graph expansion that surfaces institutionally relevant documents even when semantically distant from the query:

```
Query → vector search → CHM-0059 (recurrence case)
                              ↓
             CHM-0059 contains [[CHM-0021]], [[CHM-0004]]
                              ↓
             Inject CHM-0021 and CHM-0004 into context
             even if they didn't appear in the top-k results
```

When a technician resolves a ticket, the system automatically identifies related cases via RAG and writes Obsidian-style wikilinks into the `.md` resolution section. These links are traversed in future retrievals.

---

## The Knowledge Cycle

```
Ticket opened           Ticket resolved           Next ticket
     │                        │                        │
     ▼                        ▼                        ▼
Chat with AI ──────▶  .md saved with  ──────▶  ChromaDB indexes
                      resolution +               │
                      wikilinks                  ▼
                                          AI retrieves context
                                          and cites the source:
                                          "[CHM-2026-0021] — E05
                                           alarm: enzymatic cleaning
                                           + recalibration 150 mmHg"
```

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Gemma 4 via Ollama (`gemma4:e2b` · configurable in `.env`) |
| Embeddings | `qwen3-embedding:0.6b` — Matryoshka 1024-dim, 32K context, multilingual |
| Vector store | ChromaDB (persistent, HNSW cosine, local) |
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Database | SQLite + SQLModel |
| Knowledge store | `.md` files + ChromaDB (68 chunks) |
| Knowledge graph | D3.js v7 force-directed (90 nodes, 364 edges) |
| Frontend | HTML + Vanilla JS (no frameworks) |
| Infrastructure | Local Linux server — no Docker, no GPU required |

---

## Hardware Reference

Tested and validated on:

| Component | Spec |
|---|---|
| Machine | Dell Optiplex 3080 |
| CPU | Intel Core i5-10500 |
| RAM | **16 GB** |
| GPU | **None (CPU only)** |
| OS | Ubuntu 24.04.4 LTS |
| LLM active | gemma4:e2b (2B params, ~7.2 GB RAM) |
| Embed active | qwen3-embedding:0.6b (~639 MB RAM) |

> If more RAM is available, `gemma4:27b` produces better citation accuracy with no code changes.

---

## How to Run

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) installed and running
- Models pulled:
  ```bash
  ollama pull gemma4:e2b
  ollama pull qwen3-embedding:0.6b
  ```

### Installation

```bash
git clone https://github.com/Luiznunes13/3notes
cd 3notes

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env if needed — defaults work out of the box
```

### Seed demo data

```bash
# Base: 8 equipment types, 10 tickets, curated protocols
python scripts/seed_demo.py

# Volume: 53 resolved historical tickets (validates RAG quality)
python scripts/seed_volume.py
```

> ChromaDB indexing requires Ollama running with `qwen3-embedding:0.6b`.
> If Ollama is unavailable, the seed skips ChromaDB gracefully — SQL data is still created.

### Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access the apps

| App | URL | Role |
|---|---|---|
| Reporter | http://localhost:8000/static/reporter.html | Staff (mobile-first) |
| Dashboard | http://localhost:8000/static/dashboard.html | Technician |
| Master | http://localhost:8000/static/admin.html | Administrator |
| API Docs | http://localhost:8000/docs | — |
| Health | http://localhost:8000/health | — |

**Master login password:** `admin123`

---

## The `.md` Format — Source of Truth

Every ticket generates a `.md` file serving three simultaneous purposes:

```markdown
---
id: CHM-2026-0021
titulo: "Bomba de Infusão Fresenius Agilia — Alarme E05 oclusão contínuo"
tags: ["bomba-infusao", "alarme", "oclusao", "e05", "sensor", "uti"]
patrimonio: BI-001
setor: UTI
criticidade: alto
status: resolvido
aberto_por: Maria Silva
criado_em: 2026-04-17T10:30:00
resolvido_em: 2026-04-17T12:45:00
---

## Problema
Alarme E05 de oclusão contínuo. Equipamento não infunde medicação.

## Resolução
Sensor de oclusão obstruído por resíduo cristalizado.
Limpeza enzimática + recalibração (150 mmHg). Equipo substituído.

## Chamados relacionados
- [[CHM-2026-0004]]
- [[CHM-2026-0027]]
```

1. **Human-readable** — any technician can open and understand it
2. **ChromaDB-indexable** — vector embeddings for semantic RAG
3. **Graph-traversable** — wikilinks enable 2-hop retrieval expansion

---

## Knowledge Graph

The Master panel includes a D3.js force-directed knowledge graph:
- **Equipment nodes** (violet/large) — hubs connecting related tickets
- **Resolved tickets** (green/small) — connected to their equipment
- **Protocols & manuals** (amber/cyan) — float between clusters by shared tags
- **Edges** — solid for equipment links, dashed for shared tags, arrowed for wikilinks

With 53 simulated tickets across 12 equipment types, the graph reveals clusters of recurring problems — patterns invisible in a flat list.

---

## Responsible AI Design

- **AI suggests, human decides** — criticality is always confirmable and auditable
- **Explainable citations** — every suggestion shows `[CHM-ID]` with source snippet
- **Privacy-first** — no data leaves the hospital network (LGPD compliant)
- **RAG, not fine-tuning** — Gemma 4 stays intact; knowledge lives in `.md` files
- **Quality gate** — Master validates what enters the RAG; bad data never trains the AI
- **Threshold filtering** — cosine distance > 0.45 discards irrelevant chunks

---

## API Reference

```
GET  /health
GET  /docs

GET    /api/equipamentos
POST   /api/equipamentos
GET    /api/equipamentos/{id}
PATCH  /api/equipamentos/{id}
DELETE /api/equipamentos/{id}

GET    /api/chamados
POST   /api/chamados
GET    /api/chamados/{id}
PATCH  /api/chamados/{id}/status
PATCH  /api/chamados/{id}/criticidade
PATCH  /api/chamados/{id}/editar
PATCH  /api/chamados/{id}/validar
GET    /api/chamados/{id}/md

GET    /api/agenda?mes=YYYY-MM
POST   /api/agenda/{id}/executar
GET    /api/metricas

POST   /ai/chat
POST   /ai/chat/stream
POST   /ai/sugerir-titulo
POST   /ai/sugerir-tags
POST   /ai/preview-md
POST   /ai/confirmar-chamado

POST   /api/knowledge/upload
GET    /api/knowledge/fontes
GET    /api/knowledge/buscar?q={query}
DELETE /api/knowledge/fontes/{id}
GET    /api/knowledge/grafo
```

---

## Roadmap

- **v1.0 — Hackathon:** Text + RAG + `.md` + ChromaDB + Knowledge Graph *(this version)*
- **v1.1:** Multimodal support — images in `.md`, visual equipment analysis
- **v1.2:** AGHU integration (Brazilian federal hospital system)
- **v1.3:** Generic product — 3Notes.AI for any knowledge domain
- **v2.0:** Bulk import — index `.md` files directly from disk

---

## License

[CC-BY 4.0](LICENSE) — Luiz Filipe Pereira Nunes · NCam Tecnologia Industrial · 2026

*Gemma 4 Good Hackathon submission — Kaggle × Google DeepMind*
