# VulnScout — AI 代码漏洞审计助手

<p align="right">
  <a href="README.md">English</a>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

VulnScout 利用本地部署的 DeepSeek-Coder AI 模型，通过 [Ollama](https://ollama.com) 对源代码进行安全漏洞扫描。支持 Web UI 和 CLI 两种方式，自动适配 GPU。

## 平台支持

| 平台 | CLI | Web UI | Docker |
|------|:---:|:------:|:------:|
| Linux | ✅ | ✅ | ✅ |
| Windows | ✅ | ✅ | ⚠️（需 WSL2） |

> Windows：CLI 和 Web UI 均可正常使用。Docker 需使用 WSL2 后端。

## 功能特性

- **多语言支持**: Python、JavaScript/TypeScript、Java、C/C++
- **三级检测**: 规则预过滤 + 零样本 AI 分析 + Few-shot 模板
- **自动修复生成**: 为每个漏洞生成 unified diff 修复补丁
- **Web 界面**: 交互式仪表盘，支持 diff 对比和严重程度分类
- **CLI**: 终端工作流，支持 SARIF/JSON/Markdown 报告
- **隐私优先**: 所有计算在本地完成
- **自动硬件检测**: 自动检测 GPU 并选择最优模型

## 快速开始

### 环境要求

- Python 3.11+
- [Ollama](https://ollama.com)
- （可选）NVIDIA GPU，8GB+ 显存

### 1. 安装 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. 安装 VulnScout

```bash
git clone https://github.com/yujh129/vulnscout.git
cd vulnscout
pip install -e ".[dev]"
```

### 3. 拉取 AI 模型

```bash
vulnscout model download
# 或: ollama pull deepseek-coder:1.3b
```

### 4. 运行扫描

```bash
vulnscout scan ./my-project
vulnscout scan https://github.com/yujh129/AI-Desktop-Pet

# 导出不同格式
vulnscout scan ./my-project --format sarif --output report.sarif
vulnscout scan ./my-project --format markdown --output report.md
```

### （可选）启动 Web UI

**方式 A — 单端口（推荐）：**
```bash
cd frontend
npm install
npm run build
cd ..
uvicorn vulnscout.main:app --host 0.0.0.0 --port 8000
# 打开 http://localhost:8000
```

**方式 B — 双端口（开发模式）：**
```bash
# 终端 1
uvicorn vulnscout.main:app --host 0.0.0.0 --port 8000
# 终端 2
cd frontend && npm install && npm run dev
# 打开 http://localhost:3000
```

### Docker 部署

```bash
docker compose up -d
docker compose exec api vulnscout model download
docker compose exec api vulnscout scan /data
# 打开 http://localhost:3000
```

## CLI 命令参考

```
vulnscout scan <path>              扫描本地路径、GitHub 地址或 ZIP
vulnscout scan <path> --format json|sarif|markdown
vulnscout doctor                   诊断运行环境
vulnscout model list               列出可用 AI 模型
vulnscout model download <name>    拉取 AI 模型
vulnscout model use <name>         切换到指定模型
vulnscout model status             查看当前模型及提供商
vulnscout config init              创建配置文件
vulnscout config show              查看当前所有配置
vulnscout patch apply <vuln-id>    应用修复补丁
vulnscout patch apply-all <scan>   应用所有补丁
vulnscout github issue <scan-id>   创建 GitHub Issue
vulnscout github pr <scan-id>      创建 PR
vulnscout uninstall               彻底卸载
```

## 模型配置

### 方式 1：本地 Ollama（默认）
```bash
vulnscout config set MODEL_PROVIDER ollama
vulnscout config set MODEL_NAME deepseek-coder:1.3b
vulnscout model download
vulnscout scan ./my-project
```

### 方式 2：OpenAI API（云端）
```bash
vulnscout config set MODEL_PROVIDER openai
vulnscout config set MODEL_NAME gpt-4o-mini
vulnscout config set OPENAI_API_KEY sk-xxx
vulnscout scan ./my-project
```

### 方式 3：任意兼容 API（云端）
```bash
vulnscout config set MODEL_PROVIDER custom
vulnscout config set MODEL_NAME deepseek-chat
vulnscout config set OPENAI_BASE_URL https://api.deepseek.com/v1
vulnscout config set OPENAI_API_KEY sk-xxx
vulnscout scan ./my-project
```

## GitHub 集成

```bash
vulnscout config set GITHUB_TOKEN ghp_xxx
vulnscout github issue <scan-id>
vulnscout github pr <scan-id>
```

## 工作原理

1. **代码获取**: 本地目录、GitHub 克隆、ZIP 上传
2. **语言检测**: 自动识别代码语言
3. **AST 分块**: tree-sitter 按函数拆分代码
4. **三级分析**: 规则匹配 → 零样本 AI → Few-shot 示例
5. **修复生成**: AI 生成 diff 格式修复代码
6. **报告输出**: JSON、SARIF 2.1.0、Markdown

## 开源协议

MIT

---

*本项目通过 Vibe Coding 方式，使用 pi 编码助手构建。*
------

实验