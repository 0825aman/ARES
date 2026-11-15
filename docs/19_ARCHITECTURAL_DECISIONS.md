# 19 — Architectural Decisions (Phase 2)

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## ADR-101 — FastAPI BackgroundTasks vs. Celery/ARQ

**Decision**: Use FastAPI's built-in `BackgroundTasks` for running the research workflow.

**Alternatives considered**:
- **Celery + Redis**: Industry-standard distributed task queue. Requires a running Redis broker. Provides reliable task persistence, retries, monitoring, and distributed workers.
- **ARQ (Async Redis Queue)**: Lighter-weight async alternative to Celery. Still requires Redis.
- **FastAPI BackgroundTasks**: Built-in, zero infrastructure, executes as a coroutine in the same process.

**Rationale**: MAAR Phase 2 is a single-user local application. There is no requirement for concurrent workers, distributed execution, or task persistence across restarts. `BackgroundTasks` is sufficient and requires no additional infrastructure. The reliability trade-off (task loss on process restart) is mitigated by startup recovery logic that marks `running` runs as `failed`.

**Deferred**: Celery or ARQ will be evaluated when MAAR requires concurrent research runs, scheduled execution, or multi-user deployment (Phase 3+).

---

## ADR-102 — Alembic for Database Migrations

**Decision**: Introduce Alembic in Phase 2. Remove `create_all()` from startup.

**Alternatives considered**:
- **Continue with `create_all()`**: Works for new tables but cannot alter existing ones. Becomes a maintenance liability immediately when Phase 3 adds columns to `research_runs`.
- **Manual SQL migrations**: Error-prone, no version tracking, no rollback support.
- **SQLModel with built-in migrations**: Not compatible with the existing SQLAlchemy setup.

**Rationale**: Phase 2 introduces 4 new tables. Future phases will modify existing tables. Alembic is the standard migration tool for SQLAlchemy projects. The cost of introducing it now is low; the cost of not having it when the first `ALTER TABLE` is needed is high.

**SQLite consideration**: `render_as_batch = True` must be set in `alembic/env.py` to handle SQLite's limited `ALTER TABLE` support (it rebuilds tables instead of altering them in place).

---

## ADR-103 — Sequential Workflow vs. Multi-Agent Architecture

**Decision**: Implement Phase 2 as a sequential Python workflow. No LangGraph, no agents.

**Alternatives considered**:
- **LangGraph**: Graph-based agent orchestration. Enables complex conditional flows, human-in-the-loop, and multi-agent communication.
- **CrewAI / AutoGen**: High-level multi-agent frameworks with role-based agents.
- **Custom agent loop**: Manual implementation of tool-calling agents.

**Rationale**: The Phase 2 research workflow is a well-defined linear sequence with clear inputs and outputs at each stage. There is no requirement for dynamic branching, agent decision-making, or parallel execution that would justify agent infrastructure. Introducing LangGraph now would add substantial complexity (state graphs, node definitions, checkpoint stores) without providing any user-visible benefit. The sequential workflow design explicitly anticipates LangGraph adoption in Phase 3 — each stage is a discrete function with clean inputs and outputs, making the graph migration straightforward.

---

## ADR-104 — Tavily as Default Search Provider

**Decision**: Tavily is the default web search provider for Phase 2.

**Alternatives considered**:
- **SerpAPI (Google)**: Wraps Google Search. Accurate results. Free tier limited to 100 searches/month. Returns snippets; requires separate content fetching for all results.
- **Bing Search API (Azure)**: Reliable, well-documented. Requires Azure account. 1,000 free transactions/month.
- **DuckDuckGo unofficial API** (`duckduckgo-search` package): No key required. Returns snippets only. Rate limits enforced without notice. Unofficial — can break without warning.
- **Brave Search API**: Privacy-focused. Independent index. Free tier: 2,000 queries/month.

**Rationale**: Tavily is purpose-built for LLM-augmented research pipelines. Its key advantage is `include_raw_content=True`, which returns pre-extracted article content alongside search results. This eliminates the need to fetch and parse HTML for most results, significantly reducing execution time and failure surface. The free tier (1,000 searches/month) is sufficient for local development. The provider abstraction ensures Tavily can be swapped for any alternative by changing one environment variable.

---

## ADR-105 — OpenAI as Default LLM Provider

**Decision**: OpenAI (GPT-4o-mini) as the default LLM provider.

**Alternatives considered**:
- **Anthropic Claude**: High quality. Requires Anthropic API key. No local option.
- **Google Gemini**: Available via API. Free tier exists.
- **Ollama (local)**: Runs open-weight models locally. No API costs. Requires the user to have Ollama installed and a model downloaded. Performance varies significantly by hardware.
- **Groq**: Fast inference of open-weight models. Free tier. Requires Groq API key.

**Rationale**: GPT-4o-mini provides a strong balance of capability, speed, and cost for a research synthesis task. Its 128k context window easily accommodates the Phase 2 evidence budget (60,000 characters). The `LLMProvider` abstraction allows any of the alternatives above to be supported by implementing a new subclass. Ollama will be implemented as a Phase 3 option to support fully local operation.

---

## ADR-106 — Context Window Management Without Vector Database

**Decision**: Use keyword-overlap relevance scoring and character-budget truncation. No vector database.

**Alternatives considered**:
- **Qdrant**: High-performance vector database. Enables semantic similarity search. Requires a separate process or Docker container.
- **ChromaDB**: Embedded vector database. No separate process. Python-native.
- **FAISS**: Fast similarity search library. No persistence, in-memory only.

**Rationale**: GPT-4o-mini has a 128k token context window. Phase 2 collects at most ~30 evidence records of ~2000 tokens each = ~60,000 tokens. This fits comfortably in the context window without any retrieval step. Keyword overlap scoring (simple token intersection) is sufficient to rank evidence by relevance. Introducing a vector database in Phase 2 would add infrastructure complexity with no material benefit for this context size. Qdrant or ChromaDB will be evaluated when Phase 3 introduces multi-run evidence accumulation and cross-run retrieval requirements.

---

## ADR-107 — pypdf + python-docx for Document Extraction

**Decision**: Use `pypdf` for PDF extraction and `python-docx` for DOCX extraction.

**Alternatives considered**:
- **pdfminer.six**: More accurate PDF text extraction. More complex API. Slower.
- **pdfplumber**: Built on pdfminer.six. Better table extraction. Larger dependency.
- **unstructured**: All-in-one document parsing library. Handles 25+ formats. Requires system dependencies (libmagic, poppler, tesseract). Significantly heavier.
- **Apache Tika**: Java-based. Requires JVM. Not appropriate for a lightweight local application.

**Rationale**: `pypdf` is pure Python, actively maintained, and handles the common case (text-based PDFs) well. `python-docx` is the standard library for DOCX manipulation. Both have minimal system dependencies, making them reliable on Windows. `unstructured` would provide more capability (scanned PDFs, tables, 25+ formats) but its system dependency requirements and installation complexity are not justified for Phase 2's scope (PDF/DOCX/TXT only).

**Deferred**: OCR for scanned PDFs (requires tesseract) and table extraction are Phase 3 scope.

---

## ADR-108 — trafilatura for Web Content Extraction

**Decision**: Use `trafilatura` as the primary HTML content extractor.

**Alternatives considered**:
- **BeautifulSoup4**: General HTML parser. Requires manual extraction logic for main content. Poor at distinguishing article text from navigation/ads.
- **newspaper3k**: Designed for news article extraction. Less maintained. Limited to news-style pages.
- **readability-lxml**: Python port of Firefox Reader Mode. Good for article pages. Requires lxml system dependency.

**Rationale**: Trafilatura is specifically designed for extracting main content from web pages (equivalent to browser Reader Mode). It outperforms BeautifulSoup for article/research content and has no system dependencies beyond its Python packages. It handles a wide variety of page layouts and is actively maintained.

---

## ADR-109 — python-magic for MIME Type Validation

**Decision**: Use `python-magic` (libmagic binding) for server-side MIME type validation.

**Alternatives considered**:
- **Trust the filename extension only**: Trivially bypassed by renaming files.
- **Trust the `Content-Type` header from the browser**: Controlled by the client; not reliable for security.
- **filetype library**: Pure Python magic byte detection. No system dependency. Less comprehensive than libmagic.

**Rationale**: Accepting file uploads without server-side MIME validation is a security risk. An attacker (or misconfigured tool) could upload a malicious file with a `.pdf` extension. `python-magic` reads the file's magic bytes to determine the true type, independent of the filename or header. On Windows, `python-magic-bin` is used (bundles the libmagic DLL), avoiding the need for a separate system installation.

---

## ADR-110 — Evidence Stored in Database vs. Filesystem

**Decision**: Store evidence record content (text) in the `evidence_records` database table.

**Alternatives considered**:
- **Store extracted text as files**: Simpler initial write, but requires file I/O for every evidence lookup during synthesis.
- **Store only references, fetch on demand**: Would require re-reading uploaded files during synthesis — not idempotent if files are deleted.

**Rationale**: Evidence records are bounded in size (each chunk ≤ 8000 characters). The total evidence for a single run is at most ~60,000 characters — well within SQLite's practical limits. Storing content in the database makes evidence fully queryable and portable (no separate filesystem state required for report generation or retrieval). SQLite handles this scale efficiently.
