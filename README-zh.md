# VulnScout — AI 代码漏洞审计助手

<p align="right">
  <a href="README.md">English</a>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

VulnScout 利用本地部署的 DeepSeek-Coder AI 模型，通过 [Ollama](https://ollama.com) 对源代码进行安全漏洞扫描。支持 Web UI 和 CLI 两种方式，自动适配 GPU。

## 功能特性

- **多语言支持**: Python、JavaScript/TypeScript、Java、C/C++
- **三级检测**: 规则预过滤 + 零样本 AI 分析 + Few-shot 模板
- **自动修复生成**: 为每个漏洞生成 unified diff 格式的修复补丁
- **Web 界面**: 交互式仪表盘，支持 diff 对比和严重程度分类
- **命令行工具**: 终端优先的工作流，支持 SARIF/JSON/Markdown 报告
- **隐私优先**: 所有计算在本地完成，代码无需上传
- **自动硬件检测**: 自动检测 GPU 并选择最优模型

## 快速开始

### 环境要求

- Python 3.11+
- [Ollama](https://ollama.com) — 负责模型服务和 GPU 加速
- （可选）NVIDIA GPU，8GB 以上显存可获得 GPU 加速

### 1. 安装 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. 安装 VulnScout

```bash
# 克隆仓库
git clone <your-repo-url>
cd vulnscout
pip install -e ".[dev]"
```

### 3. 拉取 AI 模型

```bash
# 自动下载推荐模型
vulnscout model download

# 或手动拉取（效果相同）
ollama pull deepseek-coder:1.3b
```

### 4. 运行扫描

```bash
# 扫描本地目录
vulnscout scan ./my-project

# 扫描 GitHub 仓库
vulnscout scan https://github.com/user/repo

# 导出 SARIF 格式（兼容 GitHub CodeQL）
vulnscout scan ./my-project --format sarif --output report.sarif
```

### （可选）启动 Web UI

```bash
# 启动 API 服务（需先启动 Ollama）
uvicorn vulnscout.main:app --host 0.0.0.0 --port 8000

# 启动前端（另一个终端）
cd frontend && npm install && npm run dev
```

或使用 Docker Compose 一键启动：

```bash
docker compose up -d
# 打开 http://localhost:3000
```

## CLI 命令参考

```
vulnscout scan <path>              扫描本地路径、GitHub 地址或 ZIP 文件
vulnscout scan <path> --format json|sarif|markdown  指定报告格式
vulnscout scan <path> --auto-fix   自动生成修复补丁
vulnscout doctor                   诊断运行环境（GPU、Ollama、依赖）
vulnscout model list               列出可用 AI 模型
vulnscout model download <name>    通过 Ollama 拉取 AI 模型
vulnscout config init              创建配置文件
vulnscout patch apply <vuln-id>    应用修复补丁
vulnscout patch apply-all <scan>   应用某次扫描的所有补丁
```

## 工作原理

1. **代码获取**: 本地目录、GitHub 克隆或 ZIP 上传
2. **语言检测**: 自动识别 Python/JS/TS/Java/C/C++
3. **AST 分块**: 通过 tree-sitter 将代码按函数级别拆分为分析单元
4. **三级分析**:
   - 第一级：正则规则匹配已知危险模式（eval、strcpy、硬编码密钥等）
   - 第二级：零样本 AI 查询 DeepSeek-Coder 发现通用漏洞
   - 第三级：Few-shot 示例（SQL 注入、XSS）提升检测精度
5. **修复生成**: AI 生成 unified diff 格式的修复代码
6. **报告输出**: JSON、SARIF 2.1.0（兼容 CodeQL）或 Markdown

## 架构说明

详细设计文档请参考 [docs/architecture.md](docs/architecture.md)。

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## 开源协议

MIT
