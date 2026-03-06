# Agent Paperpal

<p align="center">
  <strong>🤖 Agentic AI for Academic Manuscript Formatting</strong><br/>
  <em>Automatically reformat research papers to comply with 10,000+ journal style guidelines</em>
</p>

---

## 🏗️ Architecture

Agent Paperpal uses a **5-stage agentic pipeline** powered by LangGraph to process manuscripts:

| Stage | Agent | Input | Output |
|-------|-------|-------|--------|
| 1 | **DocIngestionAgent** | .docx / .pdf / .txt | `raw_ir` |
| 2 | **DocParseAgent** | `raw_ir` | `annotated_ir` |
| 3 | **RuleInterpretAgent** | journal name | `jro` (Journal Rule Object) |
| 4 | **TransformAgent** | `annotated_ir` + `jro` | `transformed_ir` + `change_log` |
| 5 | **ValidationAgent** | `transformed_ir` + `jro` | `compliance_report` |

**Output:** RendererService converts final IR → `.docx` + LaTeX → S3 signed URLs

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI, LangGraph, Celery |
| Frontend | React 18, Vite, Tailwind CSS, Redux Toolkit |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 async) |
| Cache | Redis 7 |
| File Store | AWS S3 / MinIO (local) |
| LLM | Anthropic Claude (claude-sonnet-4-20250514) |
| CI/CD | GitHub Actions |

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Python 3.12+
- Node.js 20+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local DB/Redis/MinIO)
- [GNU Make](https://www.gnu.org/software/make/) (optional, for convenience)
- A [Google Gemini API key](https://aistudio.google.com/) (Free Tier)

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/agent-paperpal.git
cd agent-paperpal
### 1. Configure Environment
```bash
cp .env.example .env
# Open .env and set your GOOGLE_API_KEY (from AI Studio)
# Set a random SECRET_KEY for JWT
```

### 2. Start Local Infrastructure
```bash
make infra-up
```

### 3. Install Dependencies & Migrate
```bash
make install
make migrate
```

### 3. Database Migration

```bash
make migrate
```

### 4. Start Development Servers

Run these steps in separate terminal windows:

```bash
# Terminal 1: Backend
make dev-backend

# Terminal 2: Celery Worker
make dev-celery

# Terminal 3: Frontend
make dev-frontend
```

### 5. Verify

| Service | URL |
|---------|-----|
| Backend API Health | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) |
| Frontend | [http://localhost:5173](http://localhost:5173) |
| API Docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |
| API Docs (ReDoc) | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

## 📁 Project Structure

```text
agent-paperpal/
├── backend/                    # Python FastAPI application
│   ├── app/
│   │   ├── agents/             # LangGraph agent nodes
│   │   │   ├── ingestion/      # Stage 1 — Document ingestion
│   │   │   ├── parse/          # Stage 2 — NLP document parsing
│   │   │   ├── rule_interpret/ # Stage 3 — Journal rule extraction
│   │   │   ├── transform/      # Stage 4 — Rule application
│   │   │   └── validation/     # Stage 5 — Compliance validation
│   │   ├── api/v1/             # REST API endpoints
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic data contracts
│   │   ├── services/           # Business logic services
│   │   ├── middleware/         # Auth, error handling
│   │   ├── config.py           # Pydantic BaseSettings
│   │   └── main.py             # FastAPI app factory
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Backend unit tests
│   └── requirements.txt
├── frontend/                   # React 18 + Vite application
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── store/              # Redux Toolkit store
│   │   └── App.jsx
│   └── package.json
├── ml_models/                  # spaCy + HuggingFace artifacts
├── docs/                       # Architecture documentation
├── tests/                      # E2E integration tests
├── scripts/                    # Utility scripts
├── .github/workflows/          # CI/CD pipelines
├── .env.example
├── Makefile
└── README.md
```

## 🧪 Development Commands

```bash
make install          # Install all dependencies
make dev-backend      # Start backend dev server
make dev-celery       # Start celery worker
make dev-frontend     # Start frontend dev server
make test             # Run all tests (pytest + vitest)
make test-backend     # Run backend tests only
make test-frontend    # Run frontend tests only
make migrate          # Run database migrations
make migrate-create MSG="description"  # Create new migration
make lint             # Lint all code (ruff + eslint)
make format           # Auto-format Python code
```

## 🔐 Environment Variables

See [`.env.example`](.env.example) for all configuration variables with descriptions.

## 📄 License

Copyright © 2026 Agent Paperpal — HackaMined (Cactus Communications / Paperpal)
