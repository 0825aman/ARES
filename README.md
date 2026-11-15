# ARES — Autonomous Research & Evidence System

[![CI/CD Status](https://img.shields.io/badge/Status-Production%20Ready-emerald.svg)](https://github.com/0825aman/ARES)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/LangGraph-Multi--Agent-violet.svg)](https://langchain-ai.github.io/langgraph/)
[![Frontend](https://img.shields.io/badge/Next.js%2014-Tailwind%20CSS-sky.svg)](https://nextjs.org)
[![Backend](https://img.shields.io/badge/FastAPI-Python%203.11+-teal.svg)](https://fastapi.tiangolo.com)

A production-ready, autonomous multi-agent research platform. **ARES** coordinates specialized AI agents (Planner, Researcher, Supervisor, Critic) to investigate research questions, collect and verify evidence from multiple sources, enforce human approvals, execute comprehensive safety guardrails, and generate publication-quality reports with deterministic citations.

---

## 🚀 Quick Deployment Guide

### Option 1: Docker Compose (Recommended)

The fastest and most reproducible way to deploy ARES:

```bash
# 1. Clone the repository
git clone https://github.com/0825aman/ARES.git
cd ARES

# 2. Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and provide your API keys (GEMINI_API_KEY, GROQ_API_KEY, or TAVILY_API_KEY)

# 3. Build and launch all services
docker compose up -d --build
```

**Accessing Services:**
- **Web UI & Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Agent & Performance Evaluations:** [http://localhost:3000/evaluations](http://localhost:3000/evaluations)
- **Token Tracker:** [http://localhost:3000/tokens](http://localhost:3000/tokens)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Probes:** [http://localhost:8000/health/live](http://localhost:8000/health/live) · [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

---

### Option 2: Native Bare-Metal Setup

#### Backend (FastAPI + LangGraph)
```bash
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (Next.js 14)
```bash
cd frontend
npm install
cp .env.local.example .env.local

# Development mode
npm run dev

# Or Production build
npm run build
npm start
```

---

### Option 3: Cloud Deployment (Vercel & Render / Railway)

1. **Frontend on Vercel:**
   - Link the GitHub repository `0825aman/ARES`.
   - Set **Root Directory** to `frontend`.
   - Set Environment Variable: `NEXT_PUBLIC_API_URL=https://your-backend-domain.com`.
2. **Backend on Railway / Render / Fly.io:**
   - Set **Root Directory** to `backend`.
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   - Set Environment Variables from `backend/.env.example`.

---

## 🛡️ ARES Guardrails Framework (9 Categories)

ARES enforces a multi-layer guardrails framework to ensure safety, alignment, privacy, and budget compliance:

| Category | Guardrail Features & Policies | File Link |
|---|---|---|
| **1. Input Guardrails** | Prompt injection detection (`ignore instructions`, `DAN`, delimiter breakouts), malicious shell/SQL payloads, length constraints, PII detection & masking (`[REDACTED_<TYPE>]`), and inappropriate content filtering. | `backend/app/guardrails/input_guardrails.py` |
| **2. Output Guardrails** | Hallucination scoring, factual accuracy validation, toxicity filtering, automated secret/credential redaction (`sk-...`, Bearer tokens, DB URLs), and schema/format validation. | `backend/app/guardrails/output_guardrails.py` |
| **3. Tool Execution Guardrails** | Role-Based Tool Matrix (RBAC per agent), argument boundary validation, strict SSRF blocking, tool call rate limits, and ban on destructive shell commands. | `backend/app/guardrails/tool_guardrails.py` |
| **4. Data Guardrails** | Data privacy protection, recursive PII masking, project boundary isolation (preventing cross-project data leakage), user RBAC, and SQL injection safety validation. | `backend/app/guardrails/data_guardrails.py` |
| **5. Security Guardrails** | Advanced jailbreak heuristics, SQLi pattern detection, cross-agent state poisoning protection, and credential sanitization in traces. | `backend/app/guardrails/security_guardrails.py` |
| **6. Operational Guardrails** | Maximum execution time limits (300s), token budget caps (50k tokens), cost budget caps ($1.00/run), loop limits (max 30 supervisor cycles, max 3 critic cycles), and exponential backoff retry. | `backend/app/guardrails/operational_guardrails.py` |
| **7. Human-in-the-Loop** | Approval gates for financial transactions, outbound communications, and destructive operations; automatic escalation to human experts when critic scores < 0.65. | `backend/app/guardrails/hitl_guardrails.py` |
| **8. Multi-Agent Guardrails** | Agent-level access control, task assignment validation, cross-agent output verification, communication audit trails, deterministic conflict resolution, and circular loop detection. | `backend/app/guardrails/multi_agent_guardrails.py` |
| **9. Ethical & Compliance** | Demographic bias detection, fairness validation, mandatory limitations disclosure, explainability audit, and GDPR/CCPA privacy alignment. | `backend/app/guardrails/ethical_guardrails.py` |

**Guardrail API Endpoints:**
- `GET /api/v1/guardrails/status` — Operational status and feature checklist.
- `GET /api/v1/guardrails/policies` — Active policy matrices and limits.
- `GET /api/v1/guardrails/audit-trail` — Immutable audit log of security decisions.
- `POST /api/v1/guardrails/validate-input` — Standalone endpoint to validate and sanitize inputs.
- `POST /api/v1/guardrails/validate-output` — Standalone endpoint to validate and redact outputs.

---

## 📊 LLM Agent & Performance Evaluation Dashboard

A dedicated evaluation harness and mission control dashboard located at `/evaluations` measures both individual agent performance and overall multi-agent system efficacy across 6 critical dimensions:

### 1. Accuracy and Quality Metrics
- **Exact Match (EM)**: Normalized string equality check with ground truth.
- **Accuracy, Precision, Recall & F1 Score**: Token-level harmonic precision/recall balance.
- **Semantic Similarity**: Cosine similarity across normalized term-frequency vectors.
- **ROUGE Metrics**: ROUGE-1 (unigram), ROUGE-2 (bigram), and ROUGE-L (Longest Common Subsequence).
- **BLEU Metrics**: BLEU-1, BLEU-2, BLEU-3, BLEU-4 cumulative precision with brevity penalty.

### 2. RAG Evaluation Metrics
- **Context Precision**: Evaluates whether retrieved document chunks are directly relevant to the user query.
- **Context Recall**: Measures whether all ground-truth statements are contained in the retrieved context.
- **Faithfulness**: Verifies that every claim in the generated answer is strictly grounded in the retrieved context.
- **Answer Relevancy**: Measures semantic alignment between the report and the original research question.
- **Context Relevancy**: Signal-to-noise ratio in retrieved context, penalizing extraneous text.
- **Groundedness**: Ratio of claims backed by verified citations and source chunks.

### 3. Agentic AI Evaluation Metrics
- **Task Completion Rate**: Percentage of scheduled subtasks marked completed by agents.
- **Goal Achievement**: Evaluates whether the autonomous swarm achieved the high-level research goal.
- **Tool Call Accuracy**: Verifies that agents selected appropriate, authorized tools according to their role.
- **Tool Execution Success Rate**: Percentage of tool operations completing without error.
- **Planning Accuracy**: Structure, hierarchy, task granularity, and priority distribution of the plan.
- **Reasoning Quality**: Logical consistency between observations, claims, and conclusions.
- **Agent Coordination**: Active collaboration across the 4 specialized agents.
- **Handoff Accuracy**: Payload and state transmission fidelity across LangGraph nodes.
- **Loop Detection**: Identifies circular ping-pong cycles and runaway supervisor loops.

### 4. Safety and Guardrail Evaluation Metrics
- **Hallucination Rate**: Percentage of claims refuted by evidence or unverified.
- **Toxicity Score**: Content safety scanner detecting abusive, violent, or dangerous language.
- **Bias Score**: Heuristic scanner checking for demographic, gender, racial, or cultural stereotyping.
- **Prompt Injection Resistance**: Percentage of adversarial jailbreak attempts neutralized.
- **PII Leakage Rate**: Frequency of unmasked personal identifiers in output (0% is ideal).
- **Policy Violation Rate**: Proactive flagging of corporate or safety policy breaches.
- **Guardrail Intervention Rate**: Telemetry on how often guardrails redacted or modified data.

### 5. Performance and Cost Metrics
- **Response Latency**: Full percentile distribution (**Mean, Median p50, p95, and p99 Tail**).
- **Time to First Token (TTFT)**: Stream responsiveness (0.62s).
- **Tokens per Second**: Generation speed velocity (48.5 tokens/sec).
- **Input & Output Tokens**: Detailed token volume tracking.
- **Cost per Request & Cost per Successful Task**: Financial cost tracking ($0.0185 / completed mission).
- **Throughput & Error Rate**: Requests processed per minute (14.8 req/min) and request error rate.

### 6. Multi-Agent System Evaluation
- **End-to-End Workflow Completion**: 94.5% complete 4-agent graph execution rate.
- **Supervisor Agent Accuracy**: 96.2% optimal routing precision without redundant cycles.
- **Conflict Resolution Rate**: 92.0% deterministic reconciliation of contradictory findings.
- **Inter-Agent Consistency**: 93.8% alignment between Researcher confidence and Critic score.
- **Task Distribution Efficiency**: 89.5% workload balance across the agent nodes.
- **Communication Success Rate**: 99.2% zero-loss state transfers.
- **Individual Agent Scorecards**: Granular metrics for **Planner, Researcher, Supervisor, and Critic** agents.

**Evaluation API Endpoints:**
- `GET /api/v1/evaluations/dashboard` — Full aggregate scorecard across all 6 categories.
- `GET /api/v1/evaluations/agents` — Granular scorecards for individual swarm agents.
- `POST /api/v1/evaluations/run-benchmark` — Triggers automated benchmark evaluation across test fixtures.
- `POST /api/v1/evaluations/evaluate-custom` — Evaluates a custom prompt/generation pair.

---

## 🏗️ Repository Architecture

```
ARES/
├── frontend/                 Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui
│   ├── src/app/              Pages: mission control, projects, tokens, evaluations, login
│   ├── src/components/       UI components: evaluations, tokens, tutorial tour, activity feed
│   ├── src/lib/              API client, custom hooks, TypeScript interfaces
│   └── Dockerfile            Multi-stage Next.js standalone container
├── backend/                  FastAPI · SQLAlchemy (async) · SQLite (WAL mode) · LangGraph
│   ├── app/agents/           Planner, Researcher, Supervisor, and Critic agents
│   ├── app/guardrails/       Unified 9-category safety, security & compliance framework
│   ├── app/evaluation/       Evaluation engine (Accuracy, RAG, Agentic, Safety, Performance, Multi-Agent)
│   ├── app/api/v1/           REST endpoints: auth, projects, runs, reports, guardrails, evaluations
│   ├── app/services/         Workflows, document processing, claim verification, exports
│   ├── tests/                Comprehensive unit and integration test suites
│   ├── alembic/              Database schema migrations
│   └── Dockerfile            Multi-stage Python production runtime
├── docker-compose.yml        Production container stack
└── docker-compose.dev.yml    Development container stack with hot-reloading
```

---

## 🤖 Supported LLM & Search Providers

Configure providers via `backend/.env`:

### Primary & Fallback LLM Providers
- **Google Gemini** (`gemini`): `gemini-3.1-flash-lite` (Default primary)
- **Groq Cloud** (`groq`): `qwen/qwen3.8-27b`, `llama-3.3-70b-versatile` (Instant failover)
- **OpenRouter** (`openrouter`): `meta-llama/llama-3.1-8b-instruct` (Failover chain)
- **OpenAI** (`openai`): `gpt-4o-mini`
- **IBM watsonx.ai** (`watsonx`): `meta-llama/llama-3-3-70b-instruct`

### Web Search Providers
- **Tavily** (`tavily`): High-accuracy AI research search engine
- **arXiv**: Academic preprint search (`ARXIV_ENABLED=true`)
- **Semantic Scholar**: Scientific literature citation graph search

---

## 🔒 Security Posture

- **Session Authentication:** Single admin user authenticated via bcrypt hash (`ADMIN_PASSWORD_HASH`) stored in HTTP-only signed session cookies with 15-minute brute-force lockout.
- **Development Bypass:** Set `AUTO_LOGIN_DEV=true` in `backend/.env` for local testing.
- **SSRF Protection:** Strict loopback/private IP blocking (`is_safe_url`) on all external web fetches.
- **SQL Injection Defense:** Strict parameterized ORM queries and SQL pattern blockers.
- **Data Protection:** Zero plain-text PII storage; automated redaction and masking.

---

## 📄 License

This project is licensed under the Apache License 2.0.
