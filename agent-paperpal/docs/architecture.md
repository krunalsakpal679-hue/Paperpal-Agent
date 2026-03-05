# Agent Paperpal — Architecture Documentation

## System Overview

Agent Paperpal is an agentic AI system that automatically reformats academic research
manuscripts to comply with journal-specific formatting guidelines. The system supports
10,000+ journals across major style guides (APA, MLA, Vancouver, IEEE, Chicago).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Frontend                               │
│                  (Vite + Tailwind + Redux)                          │
└───────────────┬─────────────────────────────────────────────────────┘
                │ REST API + WebSocket
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                │
│              ┌─────────────────────────────┐                        │
│              │     API Layer (v1)          │                        │
│              │   /health, /jobs, /auth     │                        │
│              └──────────┬──────────────────┘                        │
│                         │                                           │
│              ┌──────────▼──────────────────┐                        │
│              │     Celery Task Queue       │                        │
│              │   (Background Processing)   │                        │
│              └──────────┬──────────────────┘                        │
│                         │                                           │
│              ┌──────────▼──────────────────┐                        │
│              │   LangGraph Pipeline        │                        │
│              │                             │                        │
│              │  Stage 1: DocIngestion      │                        │
│              │  Stage 2: DocParse (NLP)    │                        │
│              │  Stage 3: RuleInterpret     │                        │
│              │  Stage 4: Transform         │                        │
│              │  Stage 5: Validation        │                        │
│              │                             │                        │
│              │  └──▶ RendererService       │                        │
│              └─────────────────────────────┘                        │
└─────┬───────────┬───────────┬───────────┬───────────────────────────┘
      │           │           │           │
      ▼           ▼           ▼           ▼
┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│PostgreSQL││  Redis   ││  MinIO   ││ Claude   │
│   16     ││   7      ││  (S3)    ││  API     │
└──────────┘└──────────┘└──────────┘└──────────┘
```

## Pipeline Data Flow

```
Input (.docx/.pdf/.txt)
    │
    ▼
┌─ Stage 1: DocIngestionAgent ─┐
│  Read file → raw_ir          │
└──────────────┬───────────────┘
               ▼
┌─ Stage 2: DocParseAgent ─────┐
│  NLP labeling → annotated_ir │
└──────────────┬───────────────┘
               ▼
┌─ Stage 3: RuleInterpretAgent ┐
│  Extract rules → jro         │
└──────────────┬───────────────┘
               ▼
┌─ Stage 4: TransformAgent ────┐
│  Apply rules → transformed_ir│
│             + change_log      │
└──────────────┬───────────────┘
               ▼
┌─ Stage 5: ValidationAgent ───┐
│  Check compliance →           │
│  compliance_report            │
└──────────────┬───────────────┘
               ▼
┌─ RendererService ────────────┐
│  IR → .docx + LaTeX → S3    │
│  → signed URLs               │
└──────────────────────────────┘
```

## Key Design Decisions

1. **LangGraph StateGraph** — Chosen over a simple function chain because it provides
   built-in state management, error recovery, and the ability to add conditional
   routing (e.g., skip validation if transform reports zero changes).

2. **Pydantic v2 Schemas** — All inter-agent data contracts use Pydantic for runtime
   validation, serialization, and OpenAPI schema generation.

3. **Celery for Background Jobs** — Manuscript processing can take 30-120 seconds.
   Celery decouples the API response from pipeline execution.

4. **Redis Multi-Purpose** — Single Redis instance serves as JRO cache (DB 0),
   Celery broker (DB 1), and WebSocket pub/sub channel.

5. **MinIO for Local S3** — Provides API-compatible S3 for local development
   without requiring AWS credentials.
