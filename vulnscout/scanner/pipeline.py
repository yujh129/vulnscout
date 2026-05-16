from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy.orm import Session

from vulnscout.core.config import settings
from vulnscout.models.schemas import (
    Scan,
    ScanStatus,
    Vulnerability,
    Patch,
    PatchStatus,
)
from vulnscout.scanner.analyzer import Analyzer
from vulnscout.scanner.code_fetcher import CodeFetcher
from vulnscout.scanner.chunker import Chunk, chunk_file
from vulnscout.scanner.dedup import deduplicate, sort_by_severity
from vulnscout.scanner.patch_generator import generate_diff
from vulnscout.scanner.language_detector import (
    collect_target_files,
    detect_language,
    detect_project_language,
)


class ProgressCallback:
    """Callback interface for scan progress updates."""

    def on_progress(self, percent: float, current_file: str | None = None):
        pass

    def on_vuln_found(self, file: str, severity: str, title: str):
        pass

    def on_file_done(self, file: str, vuln_count: int):
        pass

    def on_scan_done(self, total_vulns: int, duration: float):
        pass


class ScanPipeline:
    """Orchestrate the full scan pipeline."""

    def __init__(self, db: Session, progress: ProgressCallback | None = None):
        self.db = db
        self.progress = progress or ProgressCallback()
        self.analyzer = Analyzer()

    def run(self, scan: Scan, source_dir: str) -> Scan:
        """Execute the full scan pipeline."""
        start_time = time.time()
        scan.status = ScanStatus.RUNNING
        self.db.commit()

        # Step 1: Collect target files
        files = collect_target_files(source_dir)
        scan.total_files = len(files)
        scan.language = detect_project_language(files)
        self.db.commit()

        if not files:
            scan.status = ScanStatus.DONE
            self.db.commit()
            return scan

        # Step 2: Analyze each file
        for i, rel_path in enumerate(files):
            lang = detect_language(rel_path)
            if not lang:
                continue

            full_path = Path(source_dir) / rel_path
            try:
                code = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Chunk the file
            chunks = chunk_file(rel_path, lang)

            file_vulns = []
            for chunk in chunks:
                # Three-tier analysis
                findings = self.analyzer.analyze(rel_path, chunk.code, lang)
                file_vulns.extend(findings)

            # Dedup + sort
            file_vulns = deduplicate(file_vulns)
            file_vulns = sort_by_severity(file_vulns)

            # Save vulnerabilities
            for f in file_vulns:
                # Find the containing chunk for this vulnerability
                vuln_chunk = None
                for c in chunks:
                    if (
                        f.get("line_start") and c.line_start
                        and c.line_start <= f["line_start"] <= c.line_end
                    ):
                        vuln_chunk = c
                        break
                vuln_code = vuln_chunk.code if vuln_chunk else (chunks[0].code if chunks else "")

                vuln = Vulnerability(
                    scan_id=scan.id,
                    file_path=rel_path,
                    line_start=f.get("line_start"),
                    line_end=f.get("line_end"),
                    cwe_id=f.get("cwe_id"),
                    severity=f.get("severity", "medium"),
                    title=f.get("title", "Unknown Vulnerability"),
                    description=f.get("description", ""),
                    vulnerable_code=vuln_code,
                )
                self.db.add(vuln)
                self.db.flush()

                # Generate fix
                fixed_code = self.analyzer.generate_fix(chunk.code, f, lang)
                if fixed_code:
                    diff = generate_diff(chunk.code, fixed_code, rel_path)
                    patch = Patch(
                        vuln_id=vuln.id,
                        diff_content=diff,
                        description=f"Auto-generated fix for {f.get('title', 'vulnerability')}",
                        status=PatchStatus.DRAFT,
                    )
                    self.db.add(patch)

            # Update counters
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for f in file_vulns:
                sev = f.get("severity", "low")
                if sev in severity_counts:
                    severity_counts[sev] += 1

            scan.vuln_count_critical += severity_counts["critical"]
            scan.vuln_count_high += severity_counts["high"]
            scan.vuln_count_medium += severity_counts["medium"]
            scan.vuln_count_low += severity_counts["low"]
            scan.scanned_files = i + 1
            self.db.commit()

            # Progress
            percent = ((i + 1) / len(files)) * 100
            self.progress.on_progress(percent, rel_path)
            if file_vulns:
                for f in file_vulns:
                    self.progress.on_vuln_found(
                        rel_path, f.get("severity", "medium"), f.get("title", "")
                    )
            self.progress.on_file_done(rel_path, len(file_vulns))

        # Done
        duration = time.time() - start_time
        scan.status = ScanStatus.DONE
        self.db.commit()

        self.progress.on_scan_done(
            scan.vuln_count_high + scan.vuln_count_critical, duration
        )

        return scan
