# VulnScout — AI-Powered Vulnerability Code Audit Assistant

<p align="right">
  <a href="README-zh.md">简体中文</a>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

VulnScout scans source code for security vulnerabilities using locally deployed
DeepSeek-Coder AI models via [Ollama](https://ollama.com). Supports Web UI and CLI,
with automatic GPU adaptation.

## Features

- **Multi-language support**: Python, JavaScript/TypeScript, Java, C/C++
- **Three-tier detection**: Rule pre-filter + zero-shot AI + few-shot templates
- **Auto-fix generation**: Unified diff patches for each vulnerability
- **Web UI**: Interactive dashboard with diff viewer and severity breakdown
- **CLI**: Terminal-first workflow with SARIF/JSON/Markdown reports
- **Privacy-first**: All processing runs locally on your machine
- **Auto hardware detection**: Automatically selects optimal model for your GPU

## Platform Support

| Platform | CLI | Web UI | Docker |
|----------|:---:|:------:|:------:|
| Linux | ✅ | ✅ | ✅ |
| Windows | ✅ | ✅ | ⚠️ (WSL2) |

> Windows: CLI and Web UI are fully supported. For Docker, use WSL2 backend.

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) — handles model serving and GPU acceleration
- (Optional) NVIDIA GPU with 8GB+ VRAM for GPU mode

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Install VulnScout

```bash
# Clone the repository
git clone https://github.com/yujh129/vulnscout.git
cd vulnscout

# Install Python backend
pip install -e ".[dev]"
```

### 3. Pull the AI model

```bash
# Auto-downloads the recommended model for your GPU
vulnscout model download

# Or pull manually (equivalent)
ollama pull deepseek-coder:1.3b
```

### 4. Run a scan

```bash
# Scan a local directory
vulnscout scan ./my-project

# Scan a GitHub repository
vulnscout scan https://github.com/user/repo

# Try scanning this sample project
vulnscout scan https://github.com/yujh129/AI-Desktop-Pet

# Export to SARIF (compatible with GitHub CodeQL)
vulnscout scan ./my-project --format sarif --output report.sarif

# Export to Markdown report
vulnscout scan ./my-project --format markdown --output report.md
```

### Optional: Start the Web UI

**Option A — One port (recommended):** Build frontend once, then API + UI on :8000

```bash
cd frontend
npm install
npm run build
cd ..
uvicorn vulnscout.main:app --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

**Option B — Two ports (dev mode):** No build needed, UI auto-reloads on changes

```bash
# Terminal 1: API server
uvicorn vulnscout.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend dev server
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Docker（备用方案）

确保已安装 [Docker](https://docs.docker.com/engine/install/)：

```bash
# 构建并启动所有服务
docker compose up -d

# 在容器内拉取 AI 模型
docker compose exec api vulnscout model download

# 运行扫描
docker compose exec api vulnscout scan /data

# 打开 http://localhost:3000
```

## CLI Reference

```
vulnscout scan <path>              Scan a local path, GitHub URL, or ZIP file
vulnscout scan <path> --format json|sarif|markdown
vulnscout scan <path> --auto-fix   Auto-generate fix patches
vulnscout doctor                   Diagnose environment (GPU, Ollama, dependencies)
vulnscout model list               List available AI models
vulnscout model download <name>    Pull an AI model via Ollama
vulnscout config init              Create configuration file
vulnscout patch apply <vuln-id>    Apply a fix patch
vulnscout patch apply-all <scan>   Apply all patches for a scan
vulnscout github issue <scan-id>    Create GitHub issues for vulnerabilities
vulnscout github pr <scan-id>       Create a PR with auto-generated fixes
vulnscout uninstall                 Completely remove VulnScout (package + data + models)
```

## How It Works

1. **Code acquisition**: Local directory, GitHub clone, or ZIP upload
2. **Language detection**: Auto-detects Python/JS/TS/Java/C/C++
3. **AST chunking**: Splits code into function-level units via tree-sitter
4. **Three-tier analysis**:
   - Tier 1: Regex rules for known dangerous patterns (eval, strcpy, hardcoded secrets)
   - Tier 2: Zero-shot AI query to DeepSeek-Coder for general vulnerabilities
   - Tier 3: Few-shot examples (SQLi, XSS) for precise detection
5. **Fix generation**: AI generates unified diff patches
6. **Reporting**: JSON, SARIF 2.1.0 (CodeQL compatible), or Markdown

## GitHub Integration

Auto-submit vulnerabilities to GitHub repositories.

### Setup

```bash
# Create a GitHub token (Settings → Developer settings → Personal access tokens)
# Then configure it:
vulnscout config set GITHUB_TOKEN ghp_xxxxxxxxxxxxxxxxxxxx
```

Or set via environment variable:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

### CLI

```bash
# Create issues for all vulnerabilities in a scan
vulnscout github issue <scan-id>

# Create a PR with auto-generated fix patches
vulnscout github pr <scan-id>

# Specify a custom repo (defaults to the scanned repo URL)
vulnscout github issue <scan-id> --repo owner/repo

# Only report critical/high severity issues
vulnscout github issue <scan-id> --severity high
```

### API

```bash
# Create issues
curl -X POST http://localhost:8000/api/v1/scans/<scan-id>/issues \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/repo", "severity": "high"}'

# Create PR
curl -X POST http://localhost:8000/api/v1/scans/<scan-id>/pr \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/repo", "branch": "vulnscout-fix", "base": "main"}'
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed design documentation.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

---

*Built with [Vibe Coding](https://github.com/yujh129/vulnscout) using [pi](https://github.com/earendil-works/pi-coding-agent) — an AI-powered coding agent.*
