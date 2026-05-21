from __future__ import annotations

from dataclasses import dataclass

@dataclass
class VulnerabilityRecord:
    file_path: str
    cwe_id: str | None

    def dedup_key(self) -> tuple:
        return (self.file_path, self.cwe_id)

def deduplicate(findings: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result = []
    for f in findings:
        key = (f.get("file_path", ""), f.get("cwe_id"))
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result

def sort_by_severity(findings: list[dict]) -> list[dict]:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(findings, key=lambda f: order.get(f.get("severity", "low"), 99))
