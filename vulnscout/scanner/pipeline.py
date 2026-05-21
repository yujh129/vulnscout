from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy.orm import Session

from vulnscout.models.schemas import Scan, ScanStatus, Vulnerability, Patch, PatchStatus
from vulnscout.scanner.analyzer import Analyzer
from vulnscout.scanner.chunker import chunk_file
from vulnscout.scanner.dedup import deduplicate, sort_by_severity
from vulnscout.scanner.patch_generator import generate_diff
from vulnscout.scanner.language_detector import collect_target_files, detect_language, detect_project_language


class ProgressCallback:
    def on_progress(self, percent: float, current_file: str | None = None): pass
    def on_vuln_found(self, file: str, severity: str, title: str): pass
    def on_file_done(self, file: str, vuln_count: int): pass
    def on_scan_done(self, total_vulns: int, duration: float): pass


class ScanPipeline:
    def __init__(self, db: Session, progress: ProgressCallback | None = None):
        self.db = db
        self.progress = progress or ProgressCallback()
        self.analyzer = Analyzer()

    def run(self, scan: Scan, source_dir: str) -> Scan:
        start_time = time.time()
        scan.status = ScanStatus.RUNNING
        self.db.commit()

        files = collect_target_files(source_dir)
        scan.total_files = len(files)
        scan.language = detect_project_language(files)
        self.db.commit()

        if not files:
            scan.status = ScanStatus.DONE
            self.db.commit()
            return scan

        for i, rel_path in enumerate(files):
            lang = detect_language(rel_path)
            if not lang:
                continue
            full_path = Path(source_dir) / rel_path
            try:
                code = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            chunks = chunk_file(str(full_path), lang)
            file_vulns = []
            for chunk in chunks:
                findings = self.analyzer.analyze(rel_path, chunk.code, lang)
                file_vulns.extend(findings)

            file_vulns = deduplicate(file_vulns)
            file_vulns = sort_by_severity(file_vulns)

            for f in file_vulns:
                vuln_chunk = None
                for c in chunks:
                    if f.get("line_start") and c.line_start and c.line_start <= f["line_start"] <= c.line_end:
                        vuln_chunk = c
                        break
                vuln_code = vuln_chunk.code if vuln_chunk else (chunks[0].code if chunks else "")
                vuln = Vulnerability(scan_id=scan.id, file_path=rel_path,
                    line_start=f.get("line_start"), line_end=f.get("line_end"),
                    cwe_id=f.get("cwe_id"), severity=f.get("severity", "medium"),
                    title=f.get("title", "Unknown Vulnerability"), description=f.get("description", ""),
                    vulnerable_code=vuln_code)
                self.db.add(vuln)
                self.db.flush()
                fixed_code = self.analyzer.generate_fix(chunk.code, f, lang)
                if fixed_code:
                    diff = generate_diff(chunk.code, fixed_code, rel_path)
                    self.db.add(Patch(vuln_id=vuln.id, diff_content=diff, description=f"Auto-generated fix for {f.get('title', 'vulnerability')}", status=PatchStatus.DRAFT))

            sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for f in file_vulns:
                sev = f.get("severity", "low")
                if sev in sev_counts:
                    sev_counts[sev] += 1
            scan.vuln_count_critical += sev_counts["critical"]
            scan.vuln_count_high += sev_counts["high"]
            scan.vuln_count_medium += sev_counts["medium"]
            scan.vuln_count_low += sev_counts["low"]
            scan.scanned_files = i + 1
            self.db.commit()
            self.progress.on_progress(((i + 1) / len(files)) * 100, rel_path)

        duration = time.time() - start_time
        scan.status = ScanStatus.DONE
        self.db.commit()
        self.progress.on_scan_done(scan.vuln_count_high + scan.vuln_count_critical, duration)
        return scan
