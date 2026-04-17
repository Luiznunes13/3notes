# 3Notes.AI — Technical Write-up

## 1. Problem Statement

Brazil's public hospital network (SUS) faces a silent crisis: over **43,000 medical devices** are out of service at any given time due to lack of structured maintenance management (source: CNES/Ministry of Health). Ventilators, autoclaves, infusion pumps — critical equipment that keeps patients alive — fail without warning because hospitals have no system to track them, schedule preventive maintenance, or learn from past failures.

The root cause is not a lack of competent technicians. It is a lack of **systems that preserve and accumulate their knowledge**. Maintenance today is managed with paper notebooks and spreadsheets. When a technician fixes a recurring fault on a ventilator, that knowledge exists only in their head. When their shift ends — or when they leave the hospital — that knowledge vanishes.

## 2. Why Knowledge Matters

The real cost of poor maintenance management is not just broken equipment. It is **the compounding loss of institutional knowledge**. A technician who has fixed the same infusion pump alarm a dozen times knows the exact sensor to replace, the correct recalibration sequence, and which replacement parts to keep in stock. A new technician facing the same problem from scratch will spend hours, delay treatment, and potentially escalate a simple fix into a critical incident.

Knowledge management in hospital maintenance is not a luxury — it is patient safety infrastructure. Every hospital should have a system that gets smarter with each resolved ticket, so that the next technician benefits from every previous one.

## 3. Solution: 3Notes.AI

**3Notes.AI** is a three-application system that transforms maintenance tickets into a living knowledge base. It is designed specifically for the infrastructure that SUS hospitals already have: a local Linux server, a network, and browsers on staff mobile devices.

The three applications work together:
- **App 1 (Reporter):** Staff reports problems via a mobile-first chat interface powered by Gemma 4. The AI collects structured data conversationally, then generates a `.md` note that the user can review, edit tags on, and confirm — inspired by Obsidian's note-taking philosophy.
- **App 2 (Dashboard):** Technicians manage the ticket queue, preventive schedule, and knowledge base. When they resolve a ticket, the system automatically updates the `.md` note and re-indexes it in ChromaDB.
- **App 3 (Gemma 4 Engine):** Gemma 4 via Ollama, running entirely on the hospital's server. ChromaDB provides vector search over all accumulated `.md` files.

## 4. How We Use Gemma 4

Gemma 4 is the **central intelligence** of 3Notes.AI — present at every step, not decorative.

**Conversational intake:** Instead of asking staff to fill out complex forms, Gemma 4 conducts a structured conversation. It follows a strict protocol: collect the reporter's name, equipment asset number, problem description, and sector — asking one question at a time. This dramatically lowers the barrier to reporting, especially for non-technical staff. The model is instructed to suggest a criticality level with justification, making the AI's reasoning transparent and auditable.

**RAG-powered responses:** Before every response, the system calls the embedding API to vectorize the user's latest message, queries ChromaDB for the most semantically similar chunks from resolved tickets, manuals, and protocols, and injects that context block into the Gemma 4 system prompt. The model is instructed: *"If you find a similar resolved ticket, suggest the same solution and cite the source."* This is how the system gets smarter over time — each resolved ticket makes the next one faster.

**Metadata generation:** After the conversation concludes and the ticket is confirmed, Gemma 4 generates a concise, descriptive title (e.g., "Bomba de Infusão BI-005 — Alarme de oclusão contínuo") and 5–10 kebab-case tags in Portuguese for semantic indexing. This structured metadata is what makes the `.md` files useful for future retrieval.

**Fallback support:** The system checks Ollama for available models on startup and automatically falls back from `gemma4:27b` to `gemma4:e4b` if the larger model is not available. This is configured via the `THREENNOTES_FALLBACK_MODEL` environment variable.

## 5. The Knowledge Cycle

The most important design decision in 3Notes.AI is treating the `.md` file as the **source of truth** — not the SQL database.

When a ticket is opened: the AI generates a `.md` with YAML frontmatter (id, title, tags, asset number, sector, criticality, reporter, timestamp) plus sections for the problem description and conversation summary. This file is saved to `knowledge/chamados/` and indexed in ChromaDB.

When the ticket is resolved: the technician enters the resolution in the Dashboard. The system appends a `## Resolução` section to the existing `.md`, updates the `status` and `resolvido_em` fields in the frontmatter, and re-indexes the updated document in ChromaDB.

The next time a staff member reports a similar problem, the RAG system will retrieve this resolved ticket as context, and Gemma 4 will reference it in its response: *"This is similar to ticket CHM-2026-0042. The previous fix was: recalibrate the pressure sensor and replace the disposable set."*

The cycle is self-reinforcing: every resolved ticket enriches the knowledge base, which improves future responses, which accelerates future resolutions.

## 6. Why RAG, Not Fine-Tuning

Fine-tuning Gemma 4 on hospital maintenance data would require periodic retraining, specialized infrastructure, and would risk overfitting to a specific hospital's data. More importantly, fine-tuning cannot incorporate new knowledge in real time.

RAG, by contrast, allows the knowledge base to grow continuously — every new resolved ticket becomes immediately available for future queries. The model itself never changes; only the context changes. This mirrors the philosophy behind Google's NotebookLM: the model is a powerful but general reasoning engine; the knowledge comes from the documents you provide.

For a hospital that resolves dozens of tickets per month, RAG means that after six months of operation, the system has a rich, searchable history of every problem and solution — and Gemma 4 can reason over all of it instantly.

## 7. Why Local-First

3Notes.AI runs entirely on the hospital's own server. No API calls leave the network. No patient-adjacent data is sent to external services. This is not just a privacy preference — it is a legal requirement under Brazil's LGPD (Lei Geral de Proteção de Dados) and essential for operating in healthcare environments.

Beyond compliance, local-first means the system works even when the hospital's internet connection is down — which is common in public hospitals in smaller Brazilian cities. Maintenance cannot wait for connectivity.

## 8. Technical Architecture

The backend is a FastAPI application with SQLModel and SQLite for relational data. The knowledge engine combines ChromaDB (persistent vector store) with the Ollama embed API for generating embeddings. The frontend uses vanilla HTML/JS with TailwindCSS CDN — no build step, no Node.js, no framework. Any technician can open the dashboard in a browser on the hospital's local network.

The `.md` file format bridges the human and machine worlds: human-readable for any technician, YAML frontmatter-parseable for SQL ingestion, and full-text embeddable for ChromaDB. One file format, three uses.

## 9. Responsible AI Design

**AI suggests, technician decides.** Criticality levels are always confirmable — the AI suggests "critical" with a justification, but the technician confirms or overrides. This keeps human judgment in the loop for all safety-relevant decisions.

**Auditable.** Every AI-suggested tag, title, and criticality level is visible to the user before confirmation. The conversation history is stored in the ticket's `.md` file.

**Non-invasive.** The `.md` files are plain text. If the AI service is down, the system degrades gracefully — tickets can still be created manually via the REST API. The knowledge base remains accessible as human-readable files.

## 10. Impact & Vision

3Notes.AI addresses an immediate, concrete problem: Brazilian public hospitals losing equipment and institutional knowledge. A hospital that deploys this system today will, in six months, have a searchable history of every maintenance ticket — and a Gemma 4 model that can reference that history to suggest solutions faster.

But the architecture is generic. A `.md`-based knowledge management system powered by local RAG could serve any domain where institutional knowledge is at risk: school maintenance, municipal infrastructure, small manufacturing facilities. The vision for v1.3 is to make 3Notes.AI a general-purpose knowledge accumulation platform — free for individuals and small teams, with an enterprise tier for organizations that need shared knowledge bases across multiple locations.

*"Every resolved ticket makes the next one faster."* That principle scales beyond hospitals. It scales to any organization that learns from its own experience — which is exactly what Gemma 4 makes possible without cloud dependency, without fine-tuning, and without sending sensitive data anywhere.

---

*3Notes.AI — Luiz Nunes · NCam Tecnologia Industrial · April 2026*
*Gemma 4 Good Hackathon · Kaggle × Google DeepMind · CC-BY 4.0*
