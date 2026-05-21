from __future__ import annotations

import json
import re
from typing import Any

import httpx
from openai import OpenAI

from vulnscout.core.config import settings

_FEW_SHOT_EXAMPLES: dict[str, list[dict[str, str]]] = {
    "python": [
        {"role": "user", "content": 'Find security vulnerabilities in this Python code:\n\n```python\ndef login(username, password):\n    query = f"SELECT * FROM users WHERE username=\'{username}\' AND password=\'{password}\'"\n    cursor.execute(query)\n    return cursor.fetchone()\n```'},
        {"role": "assistant", "content": json.dumps({"vulnerabilities": [{"cwe_id": "CWE-89", "severity": "critical", "title": "SQL Injection", "description": "User input is directly interpolated into the SQL query.", "line_start": 3, "line_end": 3, "confidence": 95}]})},
    ],
    "javascript": [
        {"role": "user", "content": 'Find security vulnerabilities in this JavaScript code:\n\n```javascript\napp.get("/user", (req, res) => {\n  const name = req.query.name;\n  res.send("<h1>Hello " + name + "</h1>");\n});\n```'},
        {"role": "assistant", "content": json.dumps({"vulnerabilities": [{"cwe_id": "CWE-79", "severity": "high", "title": "Cross-Site Scripting (XSS)", "description": "User input is concatenated into HTML without sanitization.", "line_start": 3, "line_end": 3, "confidence": 95}]})},
    ],
}

_DANGEROUS_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "python": [
        {"pattern": r"(?i)(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]", "cwe": "CWE-798", "severity": "high", "title": "Hardcoded Credential"},
        {"pattern": r"eval\s*\(", "cwe": "CWE-95", "severity": "critical", "title": "Code Injection via eval()"},
        {"pattern": r"os\.system\s*\(", "cwe": "CWE-78", "severity": "high", "title": "OS Command Injection"},
        {"pattern": r"subprocess\.(call|Popen|run)\s*\(.*shell\s*=\s*True", "cwe": "CWE-78", "severity": "high", "title": "OS Command Injection (shell=True)"},
        {"pattern": r"pickle\.(loads|load)\s*\(", "cwe": "CWE-502", "severity": "high", "title": "Insecure Deserialization (pickle)"},
        {"pattern": r"flask\.render_template_string\s*\(", "cwe": "CWE-1336", "severity": "high", "title": "Server-Side Template Injection"},
    ],
    "javascript": [
        {"pattern": r"(?i)(password|secret|api_key|token)\s*[:=]\s*['\"][^'\"]+['\"]", "cwe": "CWE-798", "severity": "high", "title": "Hardcoded Credential"},
        {"pattern": r"eval\s*\(", "cwe": "CWE-95", "severity": "critical", "title": "Code Injection via eval()"},
        {"pattern": r"new\s+Function\s*\(", "cwe": "CWE-94", "severity": "critical", "title": "Code Injection via Function()"},
    ],
    "java": [
        {"pattern": r"(?i)(password|secret|apiKey|token)\s*=\s*['\"][^'\"]+['\"]", "cwe": "CWE-798", "severity": "high", "title": "Hardcoded Credential"},
        {"pattern": r"Runtime\.getRuntime\(\)\.exec\s*\(", "cwe": "CWE-78", "severity": "high", "title": "OS Command Injection"},
    ],
    "cpp": [
        {"pattern": r"strcpy\s*\(", "cwe": "CWE-121", "severity": "critical", "title": "Buffer Overflow (strcpy)"},
        {"pattern": r"sprintf\s*\(", "cwe": "CWE-120", "severity": "high", "title": "Buffer Overflow (sprintf)"},
        {"pattern": r"gets\s*\(", "cwe": "CWE-242", "severity": "critical", "title": "Unsafe gets() usage"},
    ],
}

def _rule_check(file_path: str, code: str, language: str) -> list[dict]:
    findings = []
    patterns = _DANGEROUS_PATTERNS.get(language, [])
    lines = code.split("\n")
    for p in patterns:
        for i, line in enumerate(lines):
            if re.search(p["pattern"], line):
                findings.append({"cwe_id": p["cwe"], "severity": p["severity"], "title": p["title"], "description": f"Pattern detected: {p['pattern']}", "line_start": i + 1, "line_end": i + 1, "confidence": 80, "file_path": file_path})
    return findings

def _build_zero_shot_prompt(code: str, language: str) -> str:
    return f"You are a security code audit expert. Analyze the following {language} code for security vulnerabilities. Return results as a JSON object with a \"vulnerabilities\" array. Each vulnerability has: cwe_id, severity (critical/high/medium/low), title, description, line_start, line_end, confidence (0-100).\n\nIf no vulnerabilities found, return {{\"vulnerabilities\": []}}.\n\n```{language}\n{code}\n```"

def _build_fix_prompt(code: str, vulnerability: dict, language: str) -> str:
    return f"Generate a secure fix for the following vulnerability in {language} code.\n\nVulnerability: {vulnerability.get('title', 'Unknown')} ({vulnerability.get('cwe_id', 'N/A')})\nDescription: {vulnerability.get('description', '')}\nLines {vulnerability.get('line_start', '?')}-{vulnerability.get('line_end', '?')}\n\n```{language}\n{code}\n```\n\nReturn ONLY the fixed code wrapped in ``` fences."

def _normalize_vulns(vulns: list[dict]) -> list[dict]:
    return [_normalize_single_vuln(v) for v in vulns if isinstance(v, dict)]

def _normalize_single_vuln(v: dict) -> dict | None:
    v.setdefault("title", "").strip()
    v.setdefault("severity", "medium")
    v.setdefault("cwe_id", "unknown")
    v.setdefault("description", "")
    v.setdefault("line_start", 1)
    v.setdefault("line_end", 1)
    v.setdefault("confidence", 50)
    for int_field in ("line_start", "line_end", "confidence"):
        try:
            v[int_field] = int(v[int_field])
        except (TypeError, ValueError, KeyError):
            v[int_field] = 0
    if not v["title"]:
        return None
    skip_phrases = ("no vulnerability", "no security", "no issue", "none found", "no vulnerabilities found",
                    "the code appears", "the provided code", "i don't see", "cannot identify",
                    "does not contain", "is secure", "没有发现", "未发现漏洞", "没有漏洞")
    if v["title"].lower().strip() in skip_phrases or any(p in v["title"].lower() for p in skip_phrases):
        return None
    return v


class Analyzer:
    def __init__(self):
        self._model_available: bool | None = None
        self.client: OpenAI | None = None

    def _check_model(self) -> bool:
        if self._model_available is not None:
            return self._model_available
        if settings.is_ollama:
            try:
                r = httpx.get(f"{settings.ollama_api_url}/api/tags", timeout=2.0)
                self._model_available = r.status_code == 200
            except Exception:
                self._model_available = False
        else:
            if not settings.openai_api_key:
                self._model_available = False
            else:
                try:
                    c = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key, timeout=5.0, max_retries=0)
                    c.models.list()
                    self._model_available = True
                except Exception:
                    self._model_available = False
        return self._model_available

    def analyze(self, file_path: str, code: str, language: str, model: str | None = None) -> list[dict]:
        model = model or settings.model_name
        rule_findings = _rule_check(file_path, code, language)
        model_findings = []
        if self._check_model():
            if not hasattr(self, 'client'):
                self.client = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key, timeout=10.0, max_retries=0)
            model_findings = self._model_analyze(code, language, model)
        seen_titles = {f["title"] for f in rule_findings}
        merged = list(rule_findings)
        for mf in model_findings:
            if not isinstance(mf, dict) or "title" not in mf:
                continue
            for int_field in ("line_start", "line_end", "confidence"):
                if int_field in mf:
                    try:
                        mf[int_field] = int(mf[int_field])
                    except (TypeError, ValueError):
                        mf[int_field] = 0
            if mf["title"] not in seen_titles:
                mf["file_path"] = file_path
                merged.append(mf)
                seen_titles.add(mf["title"])
        return merged

    def _model_analyze(self, code: str, language: str, model: str) -> list[dict]:
        messages = list(_FEW_SHOT_EXAMPLES.get(language, []))
        messages.append({"role": "user", "content": _build_zero_shot_prompt(code, language)})
        try:
            response = self.client.chat.completions.create(model=model, messages=messages, temperature=0.1, max_tokens=2048)
            content = response.choices[0].message.content
            if not content:
                return []
        except Exception:
            return []
        return self._parse_model_output(content, code)

    @staticmethod
    def _parse_model_output(content: str, code: str) -> list[dict]:
        r = Analyzer._try_parse_json(content)
        if r is not None:
            return r
        r = Analyzer._try_extract_json_from_fences(content)
        if r is not None:
            return r
        r = Analyzer._try_parse_plain_text(content)
        if r:
            return r
        return []

    @staticmethod
    def _try_parse_json(content: str) -> list[dict] | None:
        content = content.strip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            return None
        vulns = result.get("vulnerabilities") or result if isinstance(result, list) else []
        if not isinstance(vulns, list) or (isinstance(vulns, list) and not vulns):
            if isinstance(result, dict):
                for alt_key in ("results", "findings", "issues", "items"):
                    vulns = result.get(alt_key, [])
                    if isinstance(vulns, list) and vulns:
                        break
        if isinstance(vulns, list):
            return _normalize_vulns(vulns)
        return []

    @staticmethod
    def _try_extract_json_from_fences(content: str) -> list[dict] | None:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if not match:
            return None
        try:
            result = json.loads(match.group(1).strip())
            vulns = result.get("vulnerabilities") or result if isinstance(result, list) else []
            if not isinstance(vulns, list) or (isinstance(vulns, list) and not vulns):
                if isinstance(result, dict):
                    for alt_key in ("results", "findings", "issues", "items"):
                        vulns = result.get(alt_key, [])
                        if isinstance(vulns, list) and vulns:
                            break
            if isinstance(vulns, list):
                return _normalize_vulns(vulns)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    @staticmethod
    def _try_parse_plain_text(content: str) -> list[dict]:
        content_lower = content.lower()
        skip_patterns = ("no vulnerability", "no security issue", "none found", "no vulnerabilities found", "is secure", "does not contain", "cannot identify", "没有发现", "未发现漏洞")
        if any(p in content_lower for p in skip_patterns) and len(content) < 200:
            return []
        vulns = []
        lines = content.split("\n")
        current = {}
        for line in lines:
            line_lower = line.lower().strip()
            cwe_match = re.search(r"cwe[:\s-]*(\d+)", line_lower)
            if cwe_match:
                current["cwe_id"] = f"CWE-{cwe_match.group(1)}"
            for sev in ("critical", "high", "medium", "low"):
                if sev in line_lower and len(line) < 30:
                    current["severity"] = sev
            if not current.get("title") and len(line.strip()) > 10 and not line.startswith(("#", "-", "*", "|")):
                current["title"] = line.strip()[:100]
            if "title" in current and len(line.strip()) > 20:
                current["description"] = current.get("description", "") + line.strip() + " "
            line_match = re.search(r"line[:\s]*(\d+)", line_lower)
            if line_match:
                current["line_start"] = int(line_match.group(1))
            if line.strip() == "" and current.get("title"):
                current = _normalize_single_vuln(current)
                if current:
                    vulns.append(current)
                current = {}
        if current.get("title"):
            current = _normalize_single_vuln(current)
            if current:
                vulns.append(current)
        return vulns

    def generate_fix(self, code: str, vulnerability: dict, language: str, model: str | None = None) -> str | None:
        if not self._check_model():
            return None
        model = model or settings.model_name
        if not hasattr(self, 'client'):
            self.client = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key, timeout=10.0, max_retries=0)
        try:
            response = self.client.chat.completions.create(model=model, messages=[{"role": "user", "content": _build_fix_prompt(code, vulnerability, language)}], temperature=0.1, max_tokens=4096)
            content = response.choices[0].message.content
            match = re.search(r"```(?:\w+)?\n(.*?)\n```", content, re.DOTALL)
            return match.group(1) if match else content
        except Exception:
            return None
