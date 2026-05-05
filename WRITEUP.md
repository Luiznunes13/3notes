# 3Notes.AI — Technical Write-up
## Gemma 4 Good Hackathon · Kaggle × Google DeepMind

---

## Overview

**3Notes.AI** is a knowledge management system for hospital maintenance teams in Brazilian public hospitals. Every resolved maintenance ticket generates a structured `.md` file that is embedded into a vector knowledge base — making the system smarter with every interaction. Built entirely on local infrastructure with no GPU required, it demonstrates that Gemma 4 can deliver real institutional value in resource-constrained environments.

---

## The Problem

Brazilian public hospitals have over **43,000 medical devices out of service** due to inadequate maintenance management (source: CNES/Ministry of Health). Maintenance today is managed with paper notebooks or shared spreadsheets — no structured history, no pattern recognition, no institutional memory.

The deeper problem is knowledge loss: when a technician leaves, the hospital loses everything they learned about how to fix recurring issues on specific equipment. The next technician starts from scratch.

---

## The Solution

3Notes.AI is organized around three types of notes — hence the name:

```
        [Master — Note 3]
             /        \
      Curation       Knowledge
         /                \
[Reporter — Note 1] — [Dashboard — Note 2]
  "What happened"       "What worked"
```

- **Note 1 (Reporter):** Staff reports a problem via AI-guided chat. The system generates a structured `.md` file.
- **Note 2 (Dashboard):** Technician resolves the ticket and documents root cause and resolution in the same `.md`.
- **Note 3 (Master):** Administrator validates which resolved tickets enter the RAG knowledge base. Manages manuals and protocols.

Together, the three notes form an institutional memory that learns from every occurrence.

---

## How Gemma 4 is Used

Gemma 4 (via Ollama) is the **central intelligence** of the system — not a decorative feature:

| Function | Implementation |
|---|---|
| **Conversational intake** | Conducts structured multi-turn chat to collect ticket data without forms |
| **RAG copilot** | Retrieves relevant `.md` context from ChromaDB before each response |
| **Source citation** | Cites previous cases as `[CHM-2026-0021]` or `[Document Name]` |
| **Title generation** | Creates concise, unique titles for each `.md` note |
| **Tag suggestion** | Suggests kebab-case Portuguese tags for semantic indexing |
| **Criticality suggestion** | Proposes urgency level with explainable justification |
| **Graph expansion** | Linked documents retrieved via wikilinks injected into context |

The system is configured via `.env` and scales from `gemma4:e2b` (2B, CPU-only) to `gemma4:27b` without any code changes.

---

## Key Technical Decisions

### 1. Deferred Embedding — The Quality Gate

Tickets are saved to SQLite and disk immediately, but **not embedded into ChromaDB** until a human administrator validates them:

```
Staff opens ticket
      ↓
SQLite ✓  +  .md on disk ✓  +  ChromaDB ✗
      ↓
Master validates (quality, relevance, no patient data)
      ↓
POST /api/chamados/{id}/validar
      ↓
Chunk → embed (qwen3-embedding:0.6b) → ChromaDB ✓
      ↓
RAG active: next queries return this context
```

A poorly described ticket stays out of the RAG permanently. The Master is the quality gate of what the AI learns.

### 2. Cosine Distance Threshold — Eliminating Citation Hallucination

The system uses **qwen3-embedding:0.6b** (Matryoshka, truncated to 1024 dims) with a cosine distance threshold of **0.45**:

```
dist < 0.45 → chunk is relevant → injected into context
dist ≥ 0.45 → chunk is discarded → model says "no similar cases found"
```

Real-world calibration on Portuguese-language hospital queries revealed a natural gap between relevant chunks (0.21–0.42) and irrelevant ones (0.57–0.62). Setting the threshold at 0.45 eliminates the zone where hallucination occurs — the model only cites sources that genuinely exist and are semantically close to the query.

Without this threshold, Gemma 4 generates citations like `[Boas Práticas — Bomba de Infusão]` for documents that do not exist. With the threshold, it correctly states "I did not find similar cases in the knowledge base."

### 3. Document-Level Graph Expansion via Wikilinks

Standard RAG retrieves documents by vector similarity alone. 3Notes.AI adds a **2-hop graph expansion** step after the initial vector search:

```
Query → vector search → [CHM-0059, CHM-0022, ...]
                              ↓
           CHM-0059 contains [[CHM-0021]], [[CHM-0004]]
                              ↓
           Fetch CHM-0021 and CHM-0004 from disk
                              ↓
           Inject as additional context: "(Via grafo — CHM-0021)"
```

When a technician resolves a ticket via the Dashboard, the system automatically identifies related cases via RAG and writes Obsidian-style wikilinks (`[[CHM-YYYY-NNNN]]`) into the `.md` resolution section. These links are later traversed during retrieval.

This approach retrieves institutionally relevant documents even when they are **semantically distant** from the query — addressing a structural limitation of pure vector similarity. It aligns with emerging research on source-level explainability in KG-augmented RAG systems (Li et al., XGRAG, 2025).

### 4. Source-Level Explainability

Every copilot response includes source cards showing which `.md` file and text snippet grounded the answer. This is not a decorative UI element — it is the primary trust mechanism for hospital staff who need to audit AI suggestions before acting on them.

```
"The E05 alarm indicates sensor occlusion [CHM-2026-0021].
 Clean with enzymatic solution and recalibrate to 150 mmHg."
              ↓
📎 Sources consulted
┌──────────────────────────────────────┐
│ CHM-2026-0021 Fresenius Agilia       │
│ "Bomba de infusão com alarme E05 de  │
│ oclusão contínuo. Sensor obstruído   │
│ por resíduo cristalizado..."         │
└──────────────────────────────────────┘
```

This design principle — **AI suggests, human decides** — is enforced at every layer: criticality is always confirmable, citations are always traceable, and the Master validates what the AI learns.

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
│  └──────┬──────┘   └────────┬─────────┘   └──────┬───────┘  │
│         └─────── FastAPI REST API ────────────────┘          │
│                       │                                      │
│             ┌─────────┴──────────┐                           │
│             │  SQLite + .md      │  ChromaDB (HNSW cosine)   │
│             │  Knowledge Store   │  68 chunks · 1024-dim     │
│             └────────────────────┘                           │
└──────────────────────────────────────────────────────────────┘
```

**Tech stack:**

| Component | Technology |
|---|---|
| LLM | Gemma 4 via Ollama (`gemma4:e2b`, configurable) |
| Embeddings | `qwen3-embedding:0.6b` — Matryoshka 1024-dim, multilingual |
| Vector store | ChromaDB (persistent, HNSW cosine) |
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Database | SQLite + SQLModel |
| Knowledge graph | D3.js v7 force-directed (90 nodes, 364 edges) |
| Frontend | HTML + Vanilla JS (no frameworks) |
| Infrastructure | Local Linux — no Docker, no GPU |

---

## Knowledge Base State

| Type | Count |
|---|---|
| Resolved tickets in RAG | 53 |
| Equipment types simulated | 12 |
| Curated protocols indexed | 4 |
| Technical manuals indexed | 1 |
| Total ChromaDB chunks | 68 |
| Knowledge graph nodes | 90 |
| Knowledge graph edges | 364 |

---

## Hardware — Running on What Hospitals Already Have

Validated on a Dell Optiplex 3080 — the kind of machine found in hospital administrative offices:

| Component | Spec |
|---|---|
| CPU | Intel Core i5-10500 |
| RAM | 16 GB |
| GPU | **None (CPU only)** |
| OS | Ubuntu 24.04.4 LTS |
| LLM | gemma4:e2b — 7.2 GB RAM |
| Embeddings | qwen3-embedding:0.6b — 639 MB RAM |

Response time per query: 15–45 seconds (CPU inference). Acceptable for maintenance workflows where a technician expects to wait for a consultation.

> Larger models (`gemma4:27b`) produce better citation accuracy. The system scales without code changes — just update `THREENNOTES_MODEL` in `.env`.

---

## Responsible AI Design

- **AI suggests, human decides** — criticality is always confirmable and auditable
- **Privacy-first** — no data leaves the hospital network (LGPD compliant)
- **RAG, not fine-tuning** — Gemma 4 stays intact; knowledge lives in `.md` files
- **Quality gate** — Master validates what enters the RAG; low-quality data is permanently excluded
- **Threshold filtering** — prevents citation hallucination
- **Explainable citations** — every suggestion cites the specific source file and snippet

---

## Results and Validation

The system was validated with 53 simulated historical maintenance tickets across 12 equipment types (ventilators, infusion pumps, monitors, defibrillators, autoclaves, X-ray equipment, oximeters).

**RAG quality test** — query: *"alarme E05 bomba de infusão"*
- Retrieved: CHM-2026-0021 (dist=0.215), CHM-2026-0004 (dist=0.270), CHM-2026-0022 (dist=0.285)
- Discarded: unrelated documents (dist > 0.57)
- Hallucinated citations: **zero**

**Graph expansion test** — query: *"bomba com equipo genérico incompatível padronização Fresenius"*
- Direct vector hit: CHM-2026-0059 (recurrence/standardization case)
- Via wikilink expansion: CHM-2026-0021 (original E05 sensor case)
- Both cited correctly in response with no hallucination

**Knowledge graph** — 90 nodes (12 equipment hubs + 53 resolved tickets + 25 protocols/manuals) connected by 364 edges. Equipment clusters reveal recurring problem patterns invisible in flat lists.

---

## Roadmap

- **v1.0 — Hackathon:** Text + RAG + `.md` + ChromaDB + Knowledge Graph (this version)
- **v1.1:** Multimodal — images in `.md`, visual equipment analysis with Gemma 4 vision
- **v1.2:** AGHU integration (Brazilian federal hospital system API)
- **v1.3:** Generic product — 3Notes.AI for any knowledge domain
- **v2.0:** Bulk import — index existing institutional `.md` files directly from disk

---

## Conclusion

3Notes.AI demonstrates that Gemma 4 can power a production-grade knowledge management system on hospital-grade hardware — no cloud, no GPU, no internet. The institutional knowledge that disappears every time a technician changes shifts is now captured, validated, and retrievable. Every resolved ticket makes the next one faster.

---

*Luiz Filipe Pereira Nunes · NCam Tecnologia Industrial · April–May 2026*
*Gemma 4 Good Hackathon · CC-BY 4.0*
