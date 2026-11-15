# ARES — 100% Free Production Deployment Guide for Render

This guide outlines step-by-step instructions for deploying the **ARES (Autonomous Research & Evidence System)** full-stack application on [Render](https://render.com) using your GitHub repository [0825aman/ARES](https://github.com/0825aman/ARES) **completely free ($0/month)**.

---

## 1. Why Render Was Asking for Money & How It Is Fixed

When deploying via Render Blueprint, two things can trigger a payment prompt:
1. **Persistent Disks (`disk: ...`)**: Render Persistent Disks are a paid add-on ($0.25/GB/month) and Render requires upgrading the web service to the paid "Starter" tier ($7/month) to attach one.
2. **Missing `plan: free`**: If `plan: free` is not explicitly declared on each service, Render's Blueprint engine defaults services to paid plans.

### The 100% Free Fix:
- We updated `render.yaml` with explicit **`plan: free`** on the backend, frontend, and database.
- We removed the paid disk directive.
- **Your data remains completely safe**: All projects, research runs, user credentials, sessions, evidence records, claims, citations, report contents (stored directly in PostgreSQL as markdown), and evaluation metrics are preserved permanently in the **Free Managed PostgreSQL Database**!

---

## 2. Architecture Overview (100% Free Tier)

```
┌─────────────────────────────────────────────────────────────┐
│                       User's Browser                        │
└──────────────┬──────────────────────────────▲───────────────┘
               │ HTTPS                        │
               ▼                              │
┌──────────────────────────────┐              │
│    Next.js Web Service       │              │
│   (ares-frontend.onrender)   │              │
│       Plan: FREE ($0)        │              │
└──────────────┬───────────────┘              │
               │ Internal / API Rewrites      │ Direct / SSE
               ▼                              │
┌──────────────────────────────┐──────────────┘
│     FastAPI Web Service      │
│    (ares-backend.onrender)   │
│       Plan: FREE ($0)        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Render PostgreSQL DB       │
│         (ares-db)            │
│       Plan: FREE ($0)        │
└──────────────────────────────┘
```

1. **Frontend**: Next.js 14 Web Service (`frontend/` root) running in standalone/SSR production mode on **Free Tier**.
2. **Backend**: FastAPI Web Service (`backend/` root) running on Uvicorn ASGI with native `$PORT` binding on **Free Tier**.
3. **Database**: Render Managed PostgreSQL service for projects, runs, citations, guardrail logs, and evaluation metrics on **Free Tier**.

---

## 3. Option A: 1-Click Deployment via Free Blueprint (Recommended)

### Step 1: Connect GitHub Repository
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top navigation and select **Blueprint**.
3. Select your GitHub repository: `0825aman/ARES`.
4. Render will read the updated `render.yaml` and verify all services are on **Free Plan ($0.00 / month)**.

### Step 2: Configure Environment Secrets
Render will ask you to supply values for your API keys:

| Variable | Description | Example / Instructions |
| :--- | :--- | :--- |
| `LLM_API_KEY` | Primary LLM API key | Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `SEARCH_API_KEY` | Web search API key | Your Tavily API key from [Tavily](https://tavily.com) |
| `ADMIN_PASSWORD_HASH` | Bcrypt password hash for admin | Generate using the Python snippet below |
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
Click **Apply**. Render will deploy all 3 services for free with **$0.00 total cost**.

---

## 4. Option B: Manual Free Web Service Setup (Zero Blueprint)

If you prefer to create the services manually in the Render UI:

### Step 1: Create Free PostgreSQL Database
1. Go to **New +** -> **PostgreSQL**.
2. **Name**: `ares-postgres`
3. **Database**: `ares`
4. **User**: `ares_user`
5. **Region**: Choose your nearest region (e.g., Oregon or Frankfurt).
6. **Plan**: Select **Free** ($0/month).
7. Click **Create Database**.
8. Copy the **Internal Database URL** (e.g. `postgres://ares_user:...@dpg-...:5432/ares`).

---

### Step 2: Create Free FastAPI Backend Web Service
1. Go to **New +** -> **Web Service**.
2. Select GitHub repo `0825aman/ARES`.
3. Set configuration:
   - **Name**: `ares-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Region**: Same region as your database.
   - **Branch**: `main`
   - **Plan**: Select **Free** ($0/month).
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health/live`
4. Under **Environment Variables**, add:
   ```env
   APP_ENV=production
   DATABASE_URL=<Paste Internal Database URL from Step 1>
   CHECKPOINT_DB_URL=./maar_checkpoints.db
   UPLOAD_DIR=./uploads
   EXPORT_DIR=./exports
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
5. Click **Create Web Service**. Note your backend URL: `https://ares-backend.onrender.com`.

---

### Step 3: Create Free Next.js Frontend Web Service
1. Go to **New +** -> **Web Service**.
2. Select GitHub repo `0825aman/ARES`.
3. Set configuration:
   - **Name**: `ares-frontend`
   - **Root Directory**: `frontend`
   - **Environment**: `Node`
   - **Region**: Same region as backend.
   - **Branch**: `main`
   - **Plan**: Select **Free** ($0/month).
   - **Build Command**: `npm install --include=dev && npm run build`
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

## 5. Database Migrations & Initial Setup

The ARES backend includes an intelligent self-bootstrapping startup engine in `backend/app/main.py`:

- **Fresh PostgreSQL DB**: Automatically creates all 20 initial tables from SQLAlchemy metadata (`research_projects`, `research_runs`, `documents`, `evidence_records`, `claims`, `evaluations`, etc.) and stamps the Alembic version to `head`.
- **Existing DB**: Automatically applies incremental Alembic migrations (`alembic upgrade head`).
- **Admin Seeding**: Seeds the `admin` user with `ADMIN_PASSWORD_HASH` on first boot.

---

## 6. Verification & Health Probes

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

## 7. How Free Tier Sleep / Wakeup Works

On Render's Free tier:
- If a free web service receives no traffic for 15 minutes, Render spins down the container into sleep mode to conserve resources.
- When a user visits `https://ares-frontend.onrender.com`, Render automatically wakes up the container within 30–50 seconds.
- Your PostgreSQL database and all data are retained.
