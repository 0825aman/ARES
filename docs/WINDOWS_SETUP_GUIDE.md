# MAAR Windows Setup & Troubleshooting Guide

This guide covers running MAAR natively on Windows using PowerShell and troubleshooting Windows-specific behaviors.

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Add Python to PATH during installation |
| Node.js | 18+ (LTS) | npm 9+ |
| PowerShell | 5.1+ or 7+ | Run as current user |

---

## 2. Native Windows Setup

### Step 1: PowerShell Execution Policy
If PowerShell blocks virtual environment scripts, run once:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 2: Backend Setup
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Generate an admin password hash:
```powershell
python -c "import bcrypt; print(bcrypt.hashpw(b'YourAdminPassword', bcrypt.gensalt()).decode())"
```
Place this hash into `ADMIN_PASSWORD_HASH` inside `backend\.env`.

Run the backend server:
```powershell
uvicorn app.main:app --reload --port 8000
```

### Step 3: Frontend Setup
In a new terminal:
```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Windows-Specific Considerations

1. **Path Formatting:** MAAR automatically normalizes file path separators (`\` vs `/`) in uploaded document processing and exports.
2. **SQLite PRAGMAs:** In Phase 6, SQLite is configured with WAL journal mode (`PRAGMA journal_mode=WAL`) and a busy timeout (`PRAGMA busy_timeout=5000`). On Windows, WAL mode prevents lock contention between simultaneous reader and writer connections.
3. **Magic Byte Fallback:** On Windows, binary file validation uses native header byte checking (`%PDF`, `PK\x03\x04`) alongside `python-magic-bin`.
4. **Port Termination:** If port 8000 or 3000 is occupied:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```
