from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VulnerabilityRecord:
    file_path: str
    line_start: int | None
    line_end: int | None
    cwe_id: str | None
    severity: str
    title: str
    description: str
    confidence: int

    def dedup_key(self) -> tuple:
        """Key for deduplication: same file, same CWE, overlapping lines."""
        return (self.file_path, self.cwe_id)


def deduplicate(findings: list[dict]) -> list[dict]:
    """Deduplicate vulnerability findings."""
    seen: set[tuple] = set()
    result = []

    for f in findings:
        record = VulnerabilityRecord(
            file_path=f.get("file_path", ""),
            line_start=f.get("line_start"),
            line_end=f.get("line_end"),
            cwe_id=f.get("cwe_id"),
            severity=f.get("severity", "medium"),
            title=f.get("title", ""),
            description=f.get("description", ""),
            confidence=f.get("confidence", 0),
        )
        key = record.dedup_key()
        if key not in seen:
            seen.add(key)
            result.append(f)

    return result


def sort_by_severity(findings: list[dict]) -> list[dict]:
    """Sort findings by severity (critical first)."""
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(findings, key=lambda f: order.get(f.get("severity", "low"), 99))
