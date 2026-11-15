# ARES — Autonomous Research & Evidence System

A production-ready, local-first web application for autonomous AI research. ARES coordinates specialized AI agents (Planner, Researcher, Supervisor, Critic) to investigate research questions, collect and verify evidence from multiple sources, enforce human approvals, and generate publication-quality reports with deterministic citations.

---

## 🚀 Quick Start with Docker (Recommended)

The fastest and most reproducible way to run ARES is with Docker Compose:

```bash
# 1. Clone or navigate to the repository
cd maar

# 2. Configure backend environment
cp backend/.env.example backend/.env
# Edit backend/.env to set your LLM_API_KEY (or SEARCH_API_KEY)

# 3. Build and launch all services
docker compose up --build
```

Access the application:
- **Web UI:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Checks:** [http://localhost:8000/health/live](http://localhost:8000/health/live) · [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
- **Prometheus Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)

> For full Docker details, volume management, and backup instructions, see [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md).

---

## 💻 Native Workstation Setup

If running without Docker, follow the setup instructions for your operating system:

### Prerequisites

| Tool | Minimum Version | Notes |
|---|---|---|
| Node.js | 18.x | Frontend runtime |
| npm | 9.x | Package manager |
| Python | 3.11 | Backend runtime |
| pip | 23.x | Python package installer |

---

### Initial Setup (One-time)

#### macOS / Linux

```bash
# 1. Backend setup
cd maar/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 2. Frontend setup
cd ../frontend
npm install
cp .env.local.example .env.local
```

#### Windows (PowerShell)

```powershell
# 1. Backend setup
cd maar\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

# 2. Frontend setup
cd ..\frontend
npm install
Copy-Item .env.local.example .env.local
```

> **Windows Note**: If script execution is restricted in PowerShell, run once:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> See [docs/WINDOWS_SETUP_GUIDE.md](docs/WINDOWS_SETUP_GUIDE.md) for detailed platform guidance.

---

### Running the Application

Open **two terminals** from the `maar/` directory:

#### Terminal 1 — Backend API
```bash
# macOS/Linux:
cd maar/backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Windows PowerShell:
cd maar\backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000
```

#### Terminal 2 — Frontend UI
```bash
# macOS/Linux or Windows:
cd maar/frontend && npm run dev
```

---

## 🌐 Local URLs

| Service | Endpoint | Description |
|---|---|---|
| Frontend UI | [http://localhost:3000](http://localhost:3000) | Next.js 14 Web Workspace |
| Login Page | [http://localhost:3000/login](http://localhost:3000/login) | Admin session authentication |
| Backend API | [http://localhost:8000](http://localhost:8000) | FastAPI REST service |
| Interactive Swagger Docs | [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI documentation |
| Liveness Probe | [http://localhost:8000/health/live](http://localhost:8000/health/live) | Fast process health check |
| Readiness Probe | [http://localhost:8000/health/ready](http://localhost:8000/health/ready) | Deep DB connection probe |
| Operational Metrics | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Thread-safe Prometheus counters |

---

## 🏗️ Architecture

```
maar/
├── frontend/             Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui
│   ├── src/app/          App routes: projects, runs, report view, login
│   ├── src/components/   UI components (activity feed, approval banner, source drawer, export panel)
│   ├── src/lib/          API client, custom hooks (useAuth, useSSE), data transformers
│   └── middleware.ts     Next.js edge middleware for route protection
├── backend/              FastAPI · SQLAlchemy (async) · SQLite (WAL mode) · LangGraph
│   ├── app/agents/       Planner, Researcher, Supervisor, and Critic agents
│   ├── app/api/v1/       REST routes: auth, projects, runs, reports, sources, evidence, metrics
│   ├── app/core/         Database, config, middleware (request ID, logging), retries, security
│   ├── app/services/     Workflows, document processing, claim verification, exports
│   └── alembic/          Database schema migrations
├── eval/                 AI Evaluation & Benchmarking framework
│   ├── dataset/          Curated evaluation questions across 6 domains
│   ├── metrics/          Structural, quality, and workflow evaluation metrics
│   └── runner.py         CLI benchmark runner (--dry-run, --all, --report-only)
└── docs/                 Architecture records, guides, and completion reports
```

---

## ⚡ Key Capabilities by Phase

| Capability | Phase | Status | Highlights |
|---|---|---|---|
| **Project Management** | Phase 1 | ✅ Complete | Create, list, inspect research projects with SQLite async persistence |
| **Sequential Workflow** | Phase 2 | ✅ Complete | Web search + document ingestion + initial report synthesis |
| **Multi-Agent Orchestration** | Phase 3 | ✅ Complete | LangGraph state graph with Planner, Researcher, and Supervisor |
| **Claim Verification & Review** | Phase 4 | ✅ Complete | Multi-provider search, atomic claim extraction, Critic revision cycles |
| **Research Workspace & Live UI** | Phase 5 | ✅ Complete | Real-time SSE streaming, Source Explorer, Evidence Drawer, Human-in-the-loop approvals, Multi-format exports (PDF, DOCX, Markdown) |
| **Production Readiness & Hardening** | Phase 6 | ✅ Complete | SQLite WAL mode & composite indexes, session auth with brute-force lockout, prompt injection defense, SSRF redirect checks, `@async_retry`, metrics & JSON logging, AI evaluation framework, and Docker containerization |

---

## 🤖 Supported LLM & Search Providers

Configure providers via `backend/.env` (see [docs/ENVIRONMENT_REFERENCE.md](docs/ENVIRONMENT_REFERENCE.md) for all options):

### LLM Providers (`LLM_PROVIDER`)
- **OpenAI** (`openai`): Default `gpt-4o-mini`
- **IBM watsonx.ai** (`watsonx`): `meta-llama/llama-3-3-70b-instruct`
- **Groq** (`groq`): `llama-3.3-70b-versatile`
- **Google Gemini** (`gemini`): `gemini-3.8-flash`
- **OpenRouter** (`openrouter`): `meta-llama/llama-3.1-8b-instruct`

### Web Search Providers (`SEARCH_PROVIDER`)
- **Tavily** (`tavily`): High-accuracy AI research search engine
- **arXiv**: Academic preprint search (`ARXIV_ENABLED=true`)
- **Semantic Scholar**: Scientific literature citation graph search

---

## 🧪 Evaluation & Benchmarking

MAAR includes an automated evaluation harness to assess multi-agent report quality and workflow efficiency:

```bash
# Run quick benchmark validation (dry run with mock data)
python eval/runner.py --dry-run

# Run benchmark against a specific question
python eval/runner.py --question-id tech-01

# Run full evaluation across all benchmark questions
python eval/runner.py --all

# Generate Markdown comparison report from past runs
python eval/runner.py --report-only
```

See [docs/EVALUATION_GUIDE.md](docs/EVALUATION_GUIDE.md) for benchmark schema and metrics documentation.

---

## 🔒 Security & Authentication

- **Authentication:** Single admin user authenticated via bcrypt hash (`ADMIN_PASSWORD_HASH`), stored in HTTP-only signed session cookies with 15-minute brute-force lockout.
- **Development Bypass:** Set `AUTO_LOGIN_DEV=true` in `backend/.env` to bypass login checks during local development.
- **Prompt Injection Defense:** All untrusted user inputs and external documents are sanitized and encapsulated within `<external_content>` tags with strict agent behavioral constraints.
- **SSRF Hardening:** Private/loopback IP address blocking with redirect destination re-verification.
- **Upload Protection:** File uploads are checked against binary magic bytes (`%PDF`, `PK\x03\x04`) and persisted using random UUID filenames to prevent path traversal.

See [docs/SECURITY.md](docs/SECURITY.md) for full security controls.

---

## 📚 Documentation Index

All technical specifications, guides, and architectural decision records are organized in [`docs/`](./docs/):

### Operational Guides (Phase 6)
- [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) — Docker Compose production and development setup
- [docs/WINDOWS_SETUP_GUIDE.md](docs/WINDOWS_SETUP_GUIDE.md) — PowerShell and native Windows developer setup
- [docs/ENVIRONMENT_REFERENCE.md](docs/ENVIRONMENT_REFERENCE.md) — Complete environment variable reference
- [docs/DATABASE_BACKUP_GUIDE.md](docs/DATABASE_BACKUP_GUIDE.md) — SQLite WAL backup and restoration procedures
- [docs/MONITORING_GUIDE.md](docs/MONITORING_GUIDE.md) — Structured logging, metrics, and health probes
- [docs/SECURITY.md](docs/SECURITY.md) — Security posture, prompt injection, and SSRF controls
- [docs/EVALUATION_GUIDE.md](docs/EVALUATION_GUIDE.md) — Benchmarking and AI evaluation instructions
- [docs/PHASE_6_COMPLETION_REPORT.md](docs/PHASE_6_COMPLETION_REPORT.md) — Phase 6 final verification report

### Architecture & Historical Specifications
- [Phase 1: Foundations](docs/01_PHASE_1_REQUIREMENTS.md) · [Technical Architecture](docs/02_TECHNICAL_ARCHITECTURE.md) · [Database Design](docs/05_DATABASE_DESIGN.md)
- [Phase 2: Research Engine](docs/10_PHASE_2_REQUIREMENTS.md) · [Workflow Design](docs/12_RESEARCH_WORKFLOW_DESIGN.md)
- [Phase 3: Multi-Agent System](docs/20_PHASE_3_REQUIREMENTS.md) · [LangGraph Architecture](docs/21_MULTI_AGENT_TECHNICAL_ARCHITECTURE.md)
- [Phase 4: Verification & Critic](docs/30_PHASE_4_IMPLEMENTATION_AUDIT.md) · [Critic Agent](docs/33_PHASE_4_AGENT_SPECIFICATIONS.md)
- [Phase 5: Live UI & Workspaces](docs/40_PHASE_5_REQUIREMENTS.md) · [SSE & Human Approval](docs/44_HUMAN_APPROVAL_WORKFLOW_DESIGN.md) · [Known Issues](docs/PHASE_5_KNOWN_ISSUES.md)
- [Phase 6: Production Readiness](docs/51_PHASE_6_PRODUCTION_READINESS_AUDIT.md) · [Roadmap](docs/52_PHASE_6_IMPLEMENTATION_ROADMAP.md) · [ADRs](docs/53_PHASE_6_ARCHITECTURAL_DECISIONS.md)

---

## 📄 License

This project is licensed under the Apache License 2.0.
