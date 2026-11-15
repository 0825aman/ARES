# ARES — Production Deployment Guide for Render

This guide outlines step-by-step instructions for deploying the **ARES (Autonomous Research & Evidence System)** full-stack application on [Render](https://render.com) using your GitHub repository [0825aman/ARES](https://github.com/0825aman/ARES).

---

## 1. Architecture Overview

The deployed system consists of three coordinated cloud resources on Render:

```
┌─────────────────────────────────────────────────────────────┐
│                       User's Browser                        │
└──────────────┬──────────────────────────────▲───────────────┘
               │ HTTPS                        │
               ▼                              │
┌──────────────────────────────┐              │
│    Next.js Web Service       │              │
│   (ares-frontend.onrender)   │              │
└──────────────┬───────────────┘              │
               │ Internal / API Rewrites      │ Direct / SSE
               ▼                              │
┌──────────────────────────────┐──────────────┘
│     FastAPI Web Service      │
│   (ares-backend.onrender)    │
└──────┬───────────────┬───────┘
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────────────────────────────────┐
│ Render Post- │ │ Render Persistent Disk (/var/data)       │
│ greSQL DB    │ │  ├── /uploads (PDF, DOCX, TXT inputs)    │
│  (ares-db)   │ │  ├── /exports (generated PDF/MD reports) │
└──────────────┘ │  └── ares_checkpoints.db (LangGraph)     │
                 └──────────────────────────────────────────┘
```

1. **Frontend**: Next.js 14 Web Service (`frontend/` root) running in standalone/SSR production mode.
2. **Backend**: FastAPI Web Service (`backend/` root) running on Uvicorn ASGI with native `$PORT` binding.
3. **Database**: Render Managed PostgreSQL service for projects, runs, citations, guardrail logs, and evaluation metrics.
4. **Persistent Disk**: Attached to the backend at `/var/data` for uploaded files, generated reports, and LangGraph multi-agent checkpoints.

---

## 2. Option A: 1-Click Deployment via Render Blueprint (Recommended)

Render Blueprints parse the included `render.yaml` at the root of the repository to automatically create and interconnect all three resources.

### Step 1: Connect GitHub Repository
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top navigation and select **Blueprint**.
3. Select your GitHub repository: `0825aman/ARES`.
4. Render will scan and display the Blueprint definition from `render.yaml`.

### Step 2: Configure Environment Secrets
Render will ask you to supply values for secrets flagged with `sync: false`:

| Variable | Description | Example / Instructions |
| :--- | :--- | :--- |
| `LLM_API_KEY` | Primary LLM API key | Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `SEARCH_API_KEY` | Web search API key | Your Tavily API key from [Tavily](https://tavily.com) |
| `ADMIN_PASSWORD_HASH` | Bcrypt password hash for admin | Generate using python snippet below |
| `GROQ_API_KEY` *(Optional)* | Rate-limit fallback LLM | Groq API Key |
| `OPENROUTER_API_KEY` *(Optional)* | Fallback open-source LLM | OpenRouter API Key |
| `OPENAI_API_KEY` *(Optional)* | Fallback OpenAI models | OpenAI Key |

#### Generating the Admin Password Hash:
Run this locally in your terminal to create a secure password hash:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YourSecurePassword123!', bcrypt.gensalt()).decode())"
```
Copy the printed output (starts with `$2b$12$...`) into the `ADMIN_PASSWORD_HASH` field.

### Step 3: Deploy
Click **Apply**. Render will automatically:
- Provision the `ares-postgres` database.
- Build the `ares-backend` container with Uvicorn.
- Create the persistent disk `ares-storage` mounted at `/var/data`.
- Build the Next.js `ares-frontend` and link the backend hostname.

---

## 3. Option B: Manual Web Service Setup (Step-by-Step)

If you prefer to configure the services individually in the Render UI:

### Step 1: Create PostgreSQL Database
1. Go to **New +** -> **PostgreSQL**.
2. **Name**: `ares-postgres`
3. **Database**: `ares`
4. **User**: `ares_user`
5. **Region**: Same region as your web services (e.g., Oregon or Frankfurt).
6. **Plan**: Free or Starter.
7. Click **Create Database**.
8. Copy the **Internal Database URL** (e.g. `postgres://ares_user:...@dpg-...:5432/ares`).

---

### Step 2: Create FastAPI Backend Web Service
1. Go to **New +** -> **Web Service**.
2. Select GitHub repo `0825aman/ARES`.
3. Set configuration:
   - **Name**: `ares-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Region**: Same as database.
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health/live`
4. Under **Advanced** -> **Disks**:
   - Click **Add Disk**.
   - **Name**: `ares-storage`
   - **Mount Path**: `/var/data`
   - **Size**: `1 GB` (or desired size)
5. Under **Environment Variables**, add:
   ```env
   APP_ENV=production
   DATABASE_URL=<Paste Internal Database URL from Step 1>
   CHECKPOINT_DB_URL=/var/data/ares_checkpoints.db
   UPLOAD_DIR=/var/data/uploads
   EXPORT_DIR=/var/data/exports
   ALLOWED_ORIGINS=https://ares-frontend.onrender.com
   AUTH_SECRET_KEY=<Click Generate or enter a random 32-char string>
   SESSION_TTL_HOURS=8
   AUTO_LOGIN_DEV=false
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD_HASH=<Your generated bcrypt hash>
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-3.1-flash-lite
   LLM_API_KEY=<Your Gemini Key>
   SEARCH_PROVIDER=tavily
   SEARCH_API_KEY=<Your Tavily Key>
   FALLBACK_LLM_PROVIDERS=groq,openrouter
   GROQ_API_KEY=<Your Groq Key>
   OPENROUTER_API_KEY=<Your OpenRouter Key>
   ```
6. Click **Create Web Service**. Note your backend URL: `https://ares-backend.onrender.com`.

---

### Step 3: Create Next.js Frontend Web Service
1. Go to **New +** -> **Web Service**.
2. Select GitHub repo `0825aman/ARES`.
3. Set configuration:
   - **Name**: `ares-frontend`
   - **Root Directory**: `frontend`
   - **Environment**: `Node`
   - **Region**: Same as backend.
   - **Branch**: `main`
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm start`
4. Under **Environment Variables**, add:
   ```env
   NODE_ENV=production
   API_URL=https://ares-backend.onrender.com
   NEXT_PUBLIC_AUTO_LOGIN_DEV=false
   AUTO_LOGIN_DEV=false
   ```
5. Click **Create Web Service**. Note your frontend URL: `https://ares-frontend.onrender.com`.

---

## 4. Database Migrations & Initial Setup

The ARES backend includes an intelligent self-bootstrapping startup engine in `backend/app/main.py`:

- **Fresh PostgreSQL DB**: Automatically creates all 20 initial tables from SQLAlchemy metadata (`research_projects`, `research_runs`, `documents`, `evidence_records`, `claims`, `evaluations`, etc.) and stamps the Alembic version to `head`.
- **Existing DB**: Automatically applies incremental Alembic migrations (`alembic upgrade head`).
- **Admin Seeding**: Seeds the `admin` user with `ADMIN_PASSWORD_HASH` on first boot.

If you ever need to run migrations manually via the Render Shell:
1. Open the **Shell** tab on `ares-backend` in Render.
2. Run:
   ```bash
   alembic upgrade head
   ```

---

## 5. Verification & Health Probes

Once both services deploy and display green `Live` status, verify the following endpoints:

| Route / Test | Target URL | Expected Result |
| :--- | :--- | :--- |
| **Backend Liveness** | `https://ares-backend.onrender.com/health/live` | HTTP 200 `{"status": "alive"}` |
| **Backend Readiness** | `https://ares-backend.onrender.com/health/ready` | HTTP 200 `{"status": "ready", "database": "ok"}` |
| **Backend API Docs** | `https://ares-backend.onrender.com/docs` | Interactive Swagger UI with all 9 Guardrails & Evaluation endpoints |
| **Frontend Home** | `https://ares-frontend.onrender.com/` | Loads Login or Dashboard with ambient looping muted video |
| **Evaluation Suite** | `https://ares-frontend.onrender.com/evaluations` | Displays all 6 benchmark categories and metrics |
| **Tokens & Cost** | `https://ares-frontend.onrender.com/tokens` | Displays model usage metrics and budget limits |

---

## 6. How Continuous Deployment (CD) Works

Render is connected to your GitHub repository `0825aman/ARES` on branch `main`:
- Every time you push a commit to `main`, Render triggers an automatic zero-downtime deployment.
- If you only modify backend code (`backend/...`), Render only rebuilds `ares-backend`.
- If you only modify frontend code (`frontend/...`), Render only rebuilds `ares-frontend`.
- You can monitor real-time build and server logs under the **Events** and **Logs** tabs of each service.

---

## 7. Troubleshooting Common Deployment Failures

### 1. Backend Port Binding Error
- **Symptom**: `Web service failed to bind to port within 15 minutes`.
- **Cause**: Uvicorn is hardcoded to port 8000 instead of `$PORT`.
- **Solution**: Ensure start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### 2. Database Connection Rejected / Dialect Error
- **Symptom**: `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres`
- **Cause**: Render passes `postgres://...` instead of `postgresql+asyncpg://...`.
- **Solution**: ARES automatically converts `postgres://` or `postgresql://` to `postgresql+asyncpg://` in `backend/app/core/database.py`. Verify `asyncpg` is in `requirements.txt`.

### 3. Cross-Origin (CORS) or Cookie Blocked
- **Symptom**: Browser shows 401 Unauthenticated or network error on API calls.
- **Solution**:
  - The Next.js frontend uses server-side rewrites configured in `next.config.mjs` (`destination: ${API_URL}/api/:path*`). This proxies API requests under the same origin, avoiding third-party cookie restrictions.
  - Make sure `API_URL` is set to your backend URL (`https://ares-backend.onrender.com`) on the frontend service.
  - Make sure `ALLOWED_ORIGINS` includes your frontend URL (`https://ares-frontend.onrender.com`) on the backend service.

### 4. Uploaded Files Disappearing After Restart
- **Symptom**: Documents or reports cannot be downloaded after a redeploy.
- **Cause**: Files were saved to the ephemeral container disk instead of the persistent disk.
- **Solution**: Ensure the Render disk is mounted at `/var/data` and that `UPLOAD_DIR=/var/data/uploads` and `EXPORT_DIR=/var/data/exports` are configured.
