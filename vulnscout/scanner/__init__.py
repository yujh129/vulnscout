from __future__ import annotations

from vulnscout.scanner.code_fetcher import CodeFetcher, CodeFetchError
from vulnscout.scanner.language_detector import (
    collect_target_files,
    detect_language,
    detect_project_language,
)
from vulnscout.scanner.chunker import chunk_file, Chunk
from vulnscout.scanner.analyzer import Analyzer
from vulnscout.scanner.dedup import deduplicate, sort_by_severity
from vulnscout.scanner.pipeline import ScanPipeline, ProgressCallback

__all__ = [
    "CodeFetcher",
    "CodeFetchError",
    "collect_target_files",
    "detect_language",
    "detect_project_language",
    "chunk_file",
    "Chunk",
    "Analyzer",
    "deduplicate",
    "sort_by_severity",
    "ScanPipeline",
    "ProgressCallback",
]
