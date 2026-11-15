# MAAR Docker Deployment Guide

This guide covers running the complete MAAR multi-agent research stack in Docker containers with Docker Compose.

---

## 1. Prerequisites

- **Docker:** Engine 20.10+ / Docker Desktop (Windows/macOS/Linux)
- **Docker Compose:** Compose v2 (`docker compose` CLI)
- **API Keys:** Tavily Search API key, OpenAI or IBM watsonx.ai credentials

---

## 2. Quick Start

### Step 1: Configure Environment Variables
Copy `.env.example` in `backend/` to `backend/.env` and configure your API keys:
```bash
cp backend/.env.example backend/.env
```
Ensure you have set:
- `LLM_PROVIDER` (e.g. `openai` or `watsonx`)
- `LLM_API_KEY`
- `SEARCH_API_KEY` (Tavily)
- `ADMIN_PASSWORD_HASH` (generate with: `python -c "import bcrypt; print(bcrypt.hashpw(b'password', bcrypt.gensalt()).decode())"`)

### Step 2: Build and Start Containers
```bash
docker compose up --build
```

### Step 3: Access the Application
- **Frontend UI:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
- **Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)

---

## 3. Data Persistence & Named Volumes

All state persists across container restarts using Docker named volumes:
- `maar-db`: SQLite database and LangGraph checkpointer state (`/app/data/maar.db`).
- `maar-uploads`: User-uploaded PDF/DOCX/TXT files (`/app/uploads`).
- `maar-exports`: Generated research reports in PDF, DOCX, Markdown (`/app/exports`).

To inspect volumes:
```bash
docker volume ls
```

To backup the database inside the running container:
```bash
docker compose exec backend python scripts/backup_db.py --source /app/data/maar.db --dest /app/data/backup.db
```

---

## 4. Development Mode with Live Reload

For active development with hot reload:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## 5. Teardown

Stop containers while keeping volumes:
```bash
docker compose down
```

Stop containers and remove volumes:
```bash
docker compose down -v
```
