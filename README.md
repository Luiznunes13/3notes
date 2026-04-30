# 3Notes.AI — Intelligent Knowledge System for Hospital Maintenance

> **"Every resolved ticket makes the next one faster."**
> Gemma 4 Good Hackathon · Kaggle × Google DeepMind · CC-BY 4.0

---

## The Problem

Brazilian public hospitals have over **43,000 medical devices out of service** due to lack of maintenance management (source: CNES/Ministry of Health). Maintenance today is managed with paper notebooks or spreadsheets — no tracking, no history, no preventive scheduling. Critical equipment like ventilators and autoclaves fail without warning.

Worse: **institutional knowledge disappears** with every shift change or staff departure. The technician who fixed that ventilator three times last year? When they leave, the hospital loses everything they learned.

---

## The Solution

**3Notes.AI** is a three-role knowledge management system for hospital maintenance, powered by RAG (Retrieval-Augmented Generation) with Gemma 4. Every interaction generates a structured `.md` file that feeds the knowledge base — **the system learns and improves with every resolved ticket**, inspired by Google's NotebookLM architecture and Obsidian's interconnected note philosophy.

### The Name: Why "3Notes"

The name reflects the three types of notes the system generates:

```
        [Master — Note 3]
             /        \
      Curation       Knowledge
         /                \
[Reporter — Note 1] — [Dashboard — Note 2]
  "What happened"       "What worked"
```

- **Note 1 (Reporter):** The staff member describes the problem. Documents *what happened*.
- **Note 2 (Dashboard):** The technician documents root cause and resolution. Documents *what worked*.
- **Note 3 (Master):** Manuals, protocols, curated docs. Documents *what should be done*.

Together, the three notes form a knowledge base that learns from every occurrence and never loses accumulated expertise — even with staff turnover.

---

### Architecture: 3 Apps

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
│         │                  │                     │           │
│         └─────── FastAPI REST API ────────────────┘           │
│                       │                                      │
│             ┌─────────┴─────────┐                            │
│             │  SQLite + .md     │  ChromaDB (HNSW cosine)    │
│             │  Knowledge Store  │  68 chunks · 1024-dim      │
│             └───────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

**App 1 — Reporter (mobile-first):** Staff reports problems via AI chat. The AI conducts the conversation, collects structured data, and generates a `.md` file with a unique title, suggested tags, and criticality — visible in an Obsidian-style preview before confirmation.

**App 2 — Dashboard (desktop-first):** Technicians manage the ticket queue, preventive schedule, and metrics. A floating AI copilot retrieves relevant past cases and cites them with `[CHM-YYYY-NNNN]` IDs. Resolutions are saved as `.md` and re-indexed in ChromaDB.

**App 3 — Master (admin):** The quality gate. Validates which tickets enter the RAG knowledge base (deferred embedding). Manages curated documents (manuals, protocols). Includes a D3.js force-directed knowledge graph showing clusters of interconnected notes — Obsidian-style.

---

## Deferred Embedding — The Key Design Decision

```
Staff opens ticket
      ↓
Saved to SQLite ✓  +  .md saved to disk ✓  +  ChromaDB ✗
      ↓
Master validates (checks quality, relevance, clinical accuracy)
      ↓
POST /api/chamados/{id}/validar
      ↓
Chunk → embed (qwen3-embedding:0.6b) → ChromaDB ✓
      ↓
RAG active: next copilot queries return this context
```

**The Master is the quality gate of what the AI learns.** A poorly described ticket stays out of the RAG — it remains in SQL and can be resolved normally, but does not contaminate the knowledge base.

---

## The Knowledge Cycle

```
Ticket opened         Ticket resolved         Next ticket
     │                      │                      │
     ▼                      ▼                      ▼
Chat with AI ──────▶ .md saved ─────────▶ ChromaDB indexes
                     with resolution        │
                                            ▼
                                     AI retrieves context
                                     and cites the source:
                                     "[CHM-2026-0021] — E05
                                      alarm: enzymatic cleaning
                                      + recalibration 150 mmHg"
```

---

## How Gemma 4 is Used

Gemma 4 is the **central intelligence** of 3Notes.AI — not decorative:

| Function | How Gemma 4 is used |
|---|---|
| **Conversational intake** | Conducts structured chat to collect ticket data without forms |
| **RAG-powered copilot** | Retrieves relevant `.md` context from ChromaDB before answering |
| **Source citation** | Cites previous cases as `[CHM-2026-0021]` or `[Document Name]` |
| **Title generation** | Creates concise, descriptive titles for each `.md` note |
| **Tag suggestion** | Suggests kebab-case PT tags for semantic indexing |
| **Criticality suggestion** | Proposes urgency level with explainable justification |
| **Fallback support** | Auto-switches between available models via Ollama |

---

## RAG Architecture — Quality over Quantity

The system uses **qwen3-embedding:0.6b** (Matryoshka, truncated to 1024 dims) with a **cosine distance threshold of 0.45**:

- Distance < 0.45 → chunk is relevant → injected into context
- Distance ≥ 0.45 → chunk is discarded → model says "no similar cases found"

This threshold eliminates citation hallucination: the model only cites sources that actually exist and are semantically close to the query. Real-world calibration showed a natural gap between relevant chunks (0.21–0.42) and irrelevant ones (0.57–0.62).

```
"pump occlusion alarm"
        │
qwen3-embedding:0.6b (1024-dim, 32K context, multilingual)
        │
ChromaDB HNSW cosine search
        │
dist=0.215 → CHM-2026-0021 ✅  injected
dist=0.270 → CHM-2026-0022 ✅  injected
dist=0.285 → CHM-2026-0004 ✅  injected
dist=0.571 → unrelated doc  ❌  discarded
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
| LLM | gemma4:e2b (2B params, 7.2 GB RAM) |
| Embed | qwen3-embedding:0.6b (639 MB RAM) |

> If more RAM is available, larger models (gemma4:27b) produce better citation accuracy.
> The system scales from 2B to 27B without any code changes — just update `THREENNOTES_MODEL` in `.env`.

---

## How to Run

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) installed and running
- LLM model: `ollama pull gemma4:e2b` (or any available gemma4 variant)
- Embedding model: `ollama pull qwen3-embedding:0.6b`

### Installation

```bash
git clone https://github.com/Luiznunes13/3notes
cd 3notes

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env if needed — defaults work out of the box
```

### Seed demo data

```bash
# Base data: 8 equipment, 10 tickets, 2 manuals, 1 protocol
python scripts/seed_demo.py

# Realistic volume: 53 resolved historical tickets (validates RAG quality)
python scripts/seed_volume.py
```

> ChromaDB indexing requires Ollama running with `qwen3-embedding:0.6b`.
> If Ollama is unavailable, the seed skips indexing gracefully — all SQL data is still created.

### Start the server

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the apps

| App | URL |
|---|---|
| Reporter (staff) | http://localhost:8000/static/reporter.html |
| Dashboard (technician) | http://localhost:8000/static/dashboard.html |
| Master (admin) | http://localhost:8000/static/admin.html |
| API Docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

**Master login:** `admin123`

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
Paciente em sedação contínua dependente da bomba.

## Resolução
Causa raiz: sensor de oclusão obstruído por resíduo cristalizado.
Procedimento: limpeza enzimática + recalibração (150 mmHg).
Equipo descartável substituído.
```

1. **Human-readable** — any technician can open and understand it
2. **ChromaDB-indexable** — vector embeddings for semantic RAG
3. **SQL-parseable** — YAML frontmatter feeds the relational database

---

## Knowledge Graph

The Master panel includes a D3.js force-directed knowledge graph showing:
- **Equipment nodes** (violet/large) — hubs connecting related tickets
- **Resolved tickets** (green/small) — connected to their equipment
- **Protocols & manuals** (amber/cyan) — float between clusters by shared tags
- **Edges** — solid for equipment links, dashed for shared tags, arrowed for wikilinks

With 53 simulated tickets across 12 equipment types, the graph reveals clusters of recurring problems — patterns invisible in a flat list.

---

## Responsible AI Design

- **AI suggests, human decides** — criticality is always confirmable and auditable
- **Explainable citations** — every suggestion includes `[CHM-ID]` source reference with snippet
- **Privacy-first** — no data leaves the hospital network (LGPD compliance)
- **RAG, not fine-tuning** — Gemma 4 stays intact; knowledge lives in `.md` files
- **Threshold filtering** — prevents citation hallucination (cosine distance > 0.45 = discarded)
- **Quality gate** — Master validates what enters the RAG; bad data never trains the AI

---

## API Endpoints

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

- **v1.0 — Hackathon:** Text + RAG + `.md` + ChromaDB + Knowledge Graph (this version)
- **v1.1:** Multimodal support (images in `.md`, visual equipment analysis)
- **v1.2:** AGHU integration (Brazilian federal hospital system)
- **v1.3:** Generic product — 3Notes.AI for any knowledge domain
  - Free: personal, local, unlimited
  - Pro: sync across devices
  - Enterprise: teams, shared knowledge base
- **v2.0:** Bulk import — index `.md` files directly from disk

---

## License

[CC-BY 4.0](LICENSE) — Luiz Filipe Pereira Nunes · NCam Tecnologia Industrial · April 2026

Gemma 4 Good Hackathon submission — Kaggle × Google DeepMind
