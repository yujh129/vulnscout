# VulnScout — AI-Powered Vulnerability Code Audit Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

VulnScout scans source code for security vulnerabilities using locally deployed 
DeepSeek-Coder AI models. Supports Web UI and CLI, with automatic GPU adaptation.

## Features

- **Multi-language support**: Python, JavaScript/TypeScript, Java, C/C++
- **Three-tier detection**: Rule pre-filter + zero-shot AI + few-shot templates
- **Auto-fix generation**: Unified diff patches for each vulnerability
- **Web UI**: Interactive dashboard with diff viewer and severity breakdown
- **CLI**: Terminal-first workflow with SARIF/JSON/Markdown reports
- **Privacy-first**: All processing runs locally on your machine
- **Auto hardware detection**: Automatically selects optimal model for your GPU

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) NVIDIA GPU with 8GB+ VRAM for GPU mode
- (Optional) llama.cpp for CPU mode

### Install from source

```bash
# Clone the repository
git clone <your-repo-url>
cd vulnscout
pip install .
```

### Install for development

```bash
pip install -e ".[dev]"
pytest
```

### Run a Scan

```bash
# Scan a local directory
vulnscout scan ./my-project

# Scan a GitHub repository
vulnscout scan https://github.com/user/repo

# Export to SARIF (compatible with GitHub CodeQL)
vulnscout scan ./my-project --format sarif --output report.sarif
```

### Start the Web UI

```bash
# Download an AI model first
vulnscout model download

# Start the API server
uvicorn vulnscout.main:app --host 0.0.0.0 --port 8000

# Open frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Or use Docker Compose:

```bash
docker compose up -d
# Open http://localhost:3000
```

## CLI Reference

```
vulnscout scan <path>              Scan a local path, GitHub URL, or ZIP file
vulnscout scan <path> --format json|sarif|markdown
vulnscout scan <path> --auto-fix   Auto-generate fix patches
vulnscout doctor                   Diagnose environment
vulnscout model list               List available AI models
vulnscout model download <name>    Download an AI model
vulnscout config init              Create configuration file
vulnscout patch apply <vuln-id>    Apply a fix patch
vulnscout patch apply-all <scan>   Apply all patches for a scan
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## Publishing to PyPI (Future)

Once the project is mature, publish with:

```bash
pip install build
python -m build
twine upload dist/*
```

## License

MIT
