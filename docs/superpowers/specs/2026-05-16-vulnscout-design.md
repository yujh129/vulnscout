# AI Vulnerability Code Audit Assistant (VulnScout)

**Date:** 2026-05-16
**Status:** Draft

## Overview

VulnScout is an open-source AI vulnerability code audit assistant powered by locally deployed DeepSeek-Coder. It scans user-uploaded code or GitHub repositories, automatically analyzes vulnerabilities, and generates fix suggestions with PR-level patches. Supports both Web UI and CLI, with automatic GPU resource adaptation.

## Target Languages (MVP)

- Python
- JavaScript / TypeScript
- Java
- C / C++

## Architecture

### System Overview

```
User Layer: Browser (Web UI) + Terminal (CLI)
                |
API Gateway: FastAPI (REST + WebSocket)
                |
Service Layer:
  - Code Parsing Service (tree-sitter AST)
  - Model Inference Worker (vLLM / llama.cpp)
  - Fix Generation Service (patch diff)
  - Report Generation Service (markdown/HTML/SARIF)
  - Git Service (clone / incremental pull)
                |
Data Layer: SQLite (SQLAlchemy + alembic)
```

### Scan Pipeline

1. **Code Fetch** — ZIP upload / `git clone --depth 1` GitHub URL / CLI path reference
2. **Language Detection & File Filter** — libmagic / linguist for language detection; filter to target file extensions; skip test files (optional)
3. **Code Chunking** — Tree-sitter AST parsing, chunk by function/method with context window
4. **Parallel Inference** — Worker Pool concurrently calling DeepSeek-Coder; streaming results via WebSocket
5. **Deduplication & Aggregation** — Merge same-file/same-line/same-type; CWE-based dedup; sort by severity
6. **Fix Generation** — Second model pass for confirmed vulnerabilities; output unified diff format
7. **Report Output** — Web UI interactive report / CLI SARIF/JSON/Markdown

### Vulnerability Detection Strategy (Three-Tier Cascade)

| Tier | Method | Coverage |
|---|---|---|
| 1. Rule Pre-filter | Tree-sitter pattern matching | Hardcoded keys, dangerous function calls, insecure random |
| 2. Zero-shot Inference | Direct code → model → vulnerability | Logic bugs, business logic flaws |
| 3. Few-shot Templates | OWASP samples + corresponding fixes | SQL injection, XSS, command injection, path traversal |

Tier 1 → Tier 2 → Tier 3: rule filter first for low-cost screening, then model deep analysis, saving token and GPU time.

### Model Inference Layer

- **Auto Hardware Detection** — `nvidia-smi` / `torch.cuda` on startup; fallback CPU mode
- **Auto Model Selection** — VRAM-based: ≥24GB → 7B quantized, ≥12GB → 3B, ≥8GB → 1.5B, <8GB/CPU → ollama external
- **Pluggable Backends** — vLLM (GPU, high throughput), llama.cpp (GPU/CPU, lightweight), Transformers (GPU, debug)
- **Auto Download** — First-run download from HuggingFace / ModelScope (CN mirror), e.g. `deepseek-coder-1.3b-instruct-q4_k_m.gguf`

## Tech Stack

### Backend

| Module | Technology | Rationale |
|---|---|---|
| Web Framework | FastAPI | Async, auto OpenAPI, native WebSocket |
| Async Tasks | Celery + Redis (optional) | Non-blocking large repo analysis |
| Model Inference | vLLM (primary) / llama.cpp (fallback) | Best GPU perf / CPU capable |
| Model Management | HuggingFace Hub / ModelScope | Auto download + CN mirror |
| Code Parsing | tree-sitter (py-tree-sitter) | Multi-language AST, sub-second |
| Git Operations | GitPython | Clone, diff generation |
| Database | SQLite (SQLAlchemy + alembic) | Zero-dependency single-machine |
| Package Management | PDM or Poetry | Modern Python packaging |
| Configuration | pydantic-settings | Type-safe config management |
| i18n | gettext / fastapi-babel | Chinese / English bilingual |

### Frontend

| Module | Technology |
|---|---|
| Build | Vite + React 18 + TypeScript |
| UI Framework | MUI (Material UI) — clean, professional |
| Code Editor | Monaco Editor (diff comparison) |
| State Management | Zustand |
| Routing | React Router v6 |
| i18n | react-i18next |
| WebSocket | Native + auto-reconnect |
| Charts | Recharts |
| HTTP Client | TanStack Query (React Query) |

### Deployment

- **Docker Compose** — Web + API + Worker + Redis one-click start
- **pip install** — CLI standalone distribution
- **Model Download** — Auto-pull on first run

## API Design

### REST Endpoints

```
POST /api/v1/scans                    # Create scan (ZIP upload / repo URL)
GET  /api/v1/scans/{id}               # Get scan status & summary
GET  /api/v1/scans/{id}/results       # List vulnerabilities (paginated)
GET  /api/v1/scans/{id}/results/{vid} # Get vulnerability detail + fix diff
GET  /api/v1/scans/{id}/report        # Download report (?format=json|markdown|sarif)

WS   /ws/v1/scans/{id}/progress       # Scan progress streaming

POST /api/v1/patches/{vid}/apply      # Apply fix (generate patch file)
POST /api/v1/scans/{id}/pr            # Create GitHub PR (requires token)
```

### WebSocket Protocol

```json
{"type": "progress",    "percent": 45, "current_file": "auth/login.py"}
{"type": "vuln_found",  "file": "auth/login.py", "severity": "high", "title": "SQL Injection"}
{"type": "file_done",   "file": "auth/login.py", "vulns": 2}
{"type": "scan_done",   "total_vulns": 12, "duration": 34.5}
```

## Data Model (SQLite)

```python
Scan:
  id, status(pending/running/done/failed), source_type(local/url/cli)
  source_path, language, total_files, scanned_files
  vuln_count(critical/high/medium/low), created_at

Vulnerability:
  id, scan_id, file_path, line_start, line_end
  cwe_id, severity, confidence
  title, description, vulnerable_code
  created_at

Patch:
  id, vuln_id, diff_content, description
  status(draft/applied/rejected)
  applied_at

Project:
  id, name, repo_url, last_scan_id, created_at
```

## CLI Design (Click)

```bash
vulnscout scan ./my-project
vulnscout scan https://github.com/xxx/repo
vulnscout scan ./file.zip

vulnscout scan . --format json
vulnscout scan . --format sarif
vulnscout scan . --output report.md

vulnscout config init
vulnscout config set model 7B
vulnscout config set backend vllm

vulnscout patch apply <vuln-id>
vulnscout patch apply-all
vulnscout scan . --auto-fix

vulnscout doctor
vulnscout model download
vulnscout model status
```

## Web UI Pages

| Page | Feature |
|---|---|
| Dashboard | Scan history, project list, statistics |
| New Scan | ZIP drag-and-drop / GitHub URL input / config options |
| Scan Progress | Real-time progress bar + streaming found vulnerabilities |
| Scan Result | Vulnerability list (filter by file/severity/CWE) |
| Vuln Detail | Code context highlight + vulnerability description + fix diff (Monaco diff editor) |
| Report | Exportable report view (print to PDF) |

### UI Design Principles

- Clean, professional interface — no emoji anywhere
- Bilingual support (Chinese / English) — toggle in header
- Clear information hierarchy — severity color coding (Critical red / High orange / Medium yellow / Low gray)
- Responsive layout — desktop-first with mobile adaptation

## Project Directory Structure

```
vulnscout/
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
│
├── vulnscout/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entry
│   ├── cli.py                      # Click CLI entry
│   ├── api/
│   │   ├── scans.py
│   │   ├── patches.py
│   │   └── ws.py
│   ├── core/
│   │   ├── config.py
│   │   ├── i18n.py
│   │   ├── detector.py             # HW probe
│   │   └── model_manager.py
│   ├── scanner/
│   │   ├── pipeline.py
│   │   ├── code_fetcher.py
│   │   ├── language_detector.py
│   │   ├── chunker.py
│   │   ├── analyzer.py
│   │   ├── dedup.py
│   │   └── patch_generator.py
│   ├── models/
│   │   ├── db.py
│   │   └── schemas.py
│   └── utils/
│       ├── git_utils.py
│       └── report_formatter.py
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   ├── i18n/
│   │   └── api/
│   ├── package.json
│   └── vite.config.ts
│
└── docs/
    ├── README.md
    ├── quickstart.md
    └── architecture.md
```

## Design Principles

- **YAGNI** — MVP focus on core scan + report + fix, no user auth/teams initially
- **Modular** — Each service has single responsibility, well-defined interfaces
- **Contributor-friendly** — Python + TypeScript, low barrier to entry
- **Isolated** — CLI and Web UI share API layer, independently testable and deployable
- **Graceful fallback** — No GPU → CPU mode; no model → clear error with setup guide
