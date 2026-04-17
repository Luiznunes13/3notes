# 3Notes.AI — Intelligent Knowledge System for Hospital Maintenance

> **"Every resolved ticket makes the next one faster."**
> Gemma 4 Good Hackathon · Kaggle × Google DeepMind · CC-BY 4.0

---

## The Problem

Brazilian public hospitals have over **43,000 medical devices out of service** due to lack of maintenance management (source: CNES/Ministry of Health). Maintenance today is managed with paper notebooks or spreadsheets — no tracking, no history, no preventive scheduling. Critical equipment like ventilators and autoclaves fail without warning.

Worse: **institutional knowledge disappears** with every shift change or staff departure. The technician who fixed that ventilator three times last year? When they leave, the hospital loses everything they learned.

---

## The Solution

**3Notes.AI** is a three-application knowledge management system for hospital maintenance, powered by RAG (Retrieval-Augmented Generation) with Gemma 4. Every interaction generates a structured `.md` file that feeds the knowledge base — **the system learns and improves with every resolved ticket**, inspired by Google's NotebookLM.

### Architecture: 3 Apps

```
┌──────────────────────────────────────────────────────────────┐
│                         3Notes.AI                            │
│                                                              │
│  ┌─────────────┐   ┌──────────────────┐   ┌──────────────┐  │
│  │  App 1      │   │  App 2           │   │  App 3       │  │
│  │  Reporter   │   │  Dashboard       │   │  Gemma 4     │  │
│  │  (Mobile)   │   │  (Desktop)       │   │  Engine      │  │
│  │             │   │                  │   │              │  │
│  │  Chat + .md │   │  Queue + Schedule│   │  Ollama +    │  │
│  │  generation │   │  Knowledge Base  │   │  ChromaDB    │  │
│  └──────┬──────┘   └────────┬─────────┘   └──────┬───────┘  │
│         │                  │                     │           │
│         └─────── FastAPI REST API ────────────────┘           │
│                       │                                      │
│             ┌─────────┴─────────┐                            │
│             │  SQLite + .md     │                            │
│             │  Knowledge Store  │                            │
│             └───────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

**App 1 — Reporter (mobile-first):** Staff reports problems via AI chat. The AI conducts the conversation, collects structured data, and generates a `.md` file with a unique title, suggested tags, and best practices — visible to the user in an Obsidian-style preview before confirmation.

**App 2 — Dashboard (desktop-first):** Technicians manage the ticket queue, preventive schedule, and metrics. They can browse the knowledge base, search semantically, upload manuals and protocols, and record resolutions that automatically update the `.md` and re-index in ChromaDB.

**App 3 — Gemma 4 Engine:** Gemma 4 via Ollama, running 100% locally. ChromaDB indexes all `.md` files as vector embeddings. Before every response, the system retrieves relevant context from ChromaDB and injects it into the prompt — **pure RAG, no fine-tuning required**.

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
                                     and suggests solution
                                     based on history
                                            │
                                            ▼
                                     "This is similar to
                                      ticket #42. Previous
                                      fix: recalibrate sensor."
```

---

## How Gemma 4 is Used

Gemma 4 is the **central intelligence** of 3Notes.AI — not decorative:

| Function | How Gemma 4 is used |
|---|---|
| **Conversational intake** | Conducts structured chat to collect ticket data without forms |
| **RAG-powered responses** | Retrieves relevant `.md` context from ChromaDB before answering |
| **Title generation** | Creates concise, descriptive titles for each `.md` note |
| **Tag suggestion** | Suggests kebab-case PT tags for semantic indexing |
| **Criticality suggestion** | Proposes urgency level with explainable justification |
| **Fallback support** | Auto-switches from `gemma4:27b` to `gemma4:e4b` if needed |

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Gemma 4 via Ollama (`gemma4:27b` · fallback: `gemma4:e4b`) |
| Embeddings | Ollama embed API + `nomic-embed-text` |
| Vector store | ChromaDB (persistent, local) |
| Backend | Python + FastAPI + Uvicorn |
| Database | SQLite + SQLModel |
| Knowledge store | `.md` files + ChromaDB |
| Frontend Reporter | HTML + TailwindCSS CDN + Vanilla JS (mobile-first) |
| Frontend Dashboard | HTML + TailwindCSS CDN + Chart.js |
| Infrastructure | Local Linux server — no Docker required |

---

## How to Run

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) installed and running
- Gemma 4 model: `ollama pull gemma4:27b` (or `gemma4:e4b` for lower hardware)
- Embedding model: `ollama pull nomic-embed-text`

### Installation

```bash
git clone https://github.com/your-repo/3notes
cd 3notes

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if needed (default settings work out of the box)
```

### Seed demo data + knowledge base

```bash
python scripts/seed_demo.py
```

This populates:
- 8 medical devices
- 6 tickets (2 resolved with `.md` + indexed, 1 in progress, 2 open, 1 critical)
- 3 preventive schedule items
- 2 technical manuals + 1 hospital protocol (pre-indexed in ChromaDB)

> Note: ChromaDB indexing requires Ollama running with `nomic-embed-text`. If Ollama is unavailable, the seed skips indexing gracefully — all SQL data is still created.

### Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the apps

| App | URL |
|---|---|
| Reporter (App 1) | http://localhost:8000/static/reporter.html |
| Dashboard (App 2) | http://localhost:8000/static/dashboard.html |
| API Docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

---

## The `.md` Format — Source of Truth

Every ticket generates a `.md` file that serves three simultaneous purposes:

```markdown
---
id: CHM-2026-0042
titulo: "Bomba de Infusao BI-005 — Alarme de oclusao continuo"
tags: ["bomba-infusao", "alarme", "oclusao", "uti", "fresenius"]
patrimonio: BI-005
setor: UTI
criticidade: alto
status: resolvido
aberto_por: Maria Silva
criado_em: 2026-04-17T10:30:00
resolvido_em: 2026-04-17T12:45:00
---

## Problema
Alarme de oclusao continuo (codigo E05). Equipamento nao infunde medicacao.

## Resolucao
Recalibracao do sensor de pressao + troca do equipo descartavel.
```

1. **Human-readable** — any technician can open and understand it
2. **ChromaDB-indexable** — vector embeddings for semantic search (RAG)
3. **SQL-parseable** — YAML frontmatter feeds the relational database automatically

---

## Responsible AI Design

- **AI suggests, technician decides** — criticality is always confirmable and auditable
- **Explainable** — every suggestion comes with a justification
- **Privacy-first** — no patient data leaves the hospital network (LGPD compliance)
- **RAG, not fine-tuning** — Gemma 4 model stays intact; knowledge lives in `.md` files
- **Transparent sourcing** — when the AI cites a previous ticket, the source is shown

---

## API Endpoints

```
GET  /health
GET  /docs

GET    /api/equipamentos
POST   /api/equipamentos
GET    /api/equipamentos/{id}
PATCH  /api/equipamentos/{id}

GET    /api/chamados
POST   /api/chamados
GET    /api/chamados/{id}
PATCH  /api/chamados/{id}/status
PATCH  /api/chamados/{id}/criticidade

GET    /api/agenda?mes=YYYY-MM
POST   /api/agenda/{id}/executar
GET    /api/metricas

POST   /ai/chat
POST   /ai/sugerir-titulo
POST   /ai/sugerir-tags
POST   /ai/preview-md
POST   /ai/confirmar-chamado

POST   /api/knowledge/upload
GET    /api/knowledge/fontes
GET    /api/knowledge/buscar?q={query}
DELETE /api/knowledge/fontes/{id}
```

---

## Roadmap

- **v1.0 — Hackathon:** Text + RAG + `.md` + ChromaDB (this version)
- **v1.1:** Multimodal support (images in `.md`, visual equipment analysis)
- **v1.2:** AGHU integration (Brazilian federal hospital system)
- **v1.3:** Generic product — 3Notes.AI for any knowledge domain
  - Free: personal, local, unlimited
  - Pro: sync across devices
  - Enterprise: teams, shared knowledge base

---

## License

[CC-BY 4.0](LICENSE) — Luiz Nunes · NCam Tecnologia Industrial · April 2026

Gemma 4 Good Hackathon submission — Kaggle × Google DeepMind
