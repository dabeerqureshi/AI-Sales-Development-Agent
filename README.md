# AI Sales Development Agent (AI SDR)

A local-first, evidence-based AI Sales Development Agent engineered for Apple Silicon (Mac M-series) and modern developer workstations.

The platform autonomously discovers real businesses from OpenStreetMap, investigates their public digital footprint (websites, booking flows, automation gaps), identifies verifiable public contacts, scores opportunities using transparent logic, and drafts hyper-personalized outreach emails—requiring explicit human review before any transmission.

---

## 🌟 Key Architecture & Principles

- **Local-First AI**: Runs inference locally via **Ollama** and **Qwen3 4B**, eliminating third-party API costs and protecting prospect data privacy.
- **Evidence-Based Prospecting**: No fabricated decision-makers, invented email addresses, or imagined customer problems. All attributes are tied to verifiable sources (OpenStreetMap element IDs and crawled URLs).
- **Model Context Protocol (MCP)**: Tool execution and external data acquisition are cleanly isolated through standardized MCP servers.
- **Human-in-the-Loop Safeguards**: Emails remain as editable drafts until explicitly approved and sent.

---

## 🛠 Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript | Responsive operator interface |
| **Styling** | Tailwind CSS, Lucide Icons | Dark-mode interface |
| **Backend** | Python 3.12, FastAPI, Pydantic v2 | High-performance REST API |
| **Database** | SQLite 3, SQLAlchemy 2.0 | Zero-dependency local persistence |
| **Local AI** | Ollama, Qwen3 4B | Local reasoning & draft synthesis |
| **Testing** | Pytest, Pytest-Asyncio | Automated backend test coverage |

---

## 📋 Prerequisites

- **macOS** (or Linux)
- **Node.js**: v20+ (`node --version`)
- **Python**: 3.12+ (`python3.12 --version`)
- **Ollama**: v0.4+ (`ollama --version`)
- **Git**

---

## 🚀 Getting Started

### 1. Clone & Setup Ollama

Ensure Ollama is running and download the default model:
```bash
# Start Ollama daemon (if not already running)
ollama serve

# In another terminal, pull the required local model
ollama pull qwen3:4b
```

### 2. Backend Setup (FastAPI)

```bash
cd backend

# Create Python 3.12 virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
uvicorn app.main:app --reload --port 8000
```

- API Base: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Health Diagnostics:
  - System: `http://localhost:8000/health`
  - Database: `http://localhost:8000/health/database`
  - Local AI: `http://localhost:8000/health/ollama`

### 3. Frontend Setup (Next.js)

```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server on port 3000
npm run dev
```

- Open: `http://localhost:3000` in your web browser.

---

## 🧪 Automated Testing

### Backend Test Suite
Run unit and integration tests with Pytest:
```bash
cd backend
.venv/bin/pytest -v
```

The test suite validates:
- System `/health` endpoint status.
- SQLite database connection, queries, and error handling.
- Ollama service diagnostics (connected, model missing, server offline).
- Pydantic configuration loader and environment defaults.

### Frontend Typecheck & Build
```bash
cd frontend
npm run build
```

---

## 🗺 Implementation Roadmap

- [x] **Milestone 01**: Full-stack foundation (FastAPI, Next.js 15, SQLite, Ollama diagnostics, Pytest)
- [x] **Milestone 02**: Business Discovery Engine (OpenStreetMap/Overpass API & FastMCP integration)
- [x] **Milestone 03**: Website Research Engine (HTTPX, Trafilatura, booking tool & form detection)
- [x] **Milestone 04**: Public Contact Discovery (Verified email, phone & practitioner resolution)
- [x] **Milestone 05**: AI Qualification & Scoring (0–100 deterministic Python rules + Qwen3 4B opportunity synthesis)
- [x] **Milestone 06**: AI Email Studio (Personalized draft generation, citation validation, draft versioning)
- [x] **Milestone 07**: CRM Pipeline & Suppression Gate (Kanban board, suppression blocklist, activity audit trail)
- [x] **Milestone 08**: Gmail API Integration & Human Gate (Google OAuth 2.0, developer simulator, human authorization)
- [x] **Milestone 09**: Follow-Up Automation & Worker (Native async worker, reply detection, stop-sequence rule)
- [x] **Milestone 10**: Production Hardening & Release (E2E lifecycle test suite, 8GB Mac tuning, WAL mode, Runbook)

---

## 📖 Comprehensive Documentation & Runbook

For in-depth operational procedures, hardware optimization budgets, Google OAuth configuration, and operator workflows, consult:
- **[docs/RUNBOOK.md](docs/RUNBOOK.md)**: Operator runbook & setup guide.
- **[docs/MASTER_SPECIFICATION.md](docs/MASTER_SPECIFICATION.md)**: Architectural contracts & specification.

---

## 📄 License
MIT License. Built with open-source tools.
