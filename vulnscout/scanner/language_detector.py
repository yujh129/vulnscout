from __future__ import annotations

from pathlib import Path

# Map of language to file extensions
LANGUAGE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py", ".pyi", ".pyx"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "java": {".java"},
    "c": {".c", ".h"},
    "cpp": {".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"},
}

# Map of extension to language (for single file lookup)
EXTENSION_TO_LANGUAGE: dict[str, str] = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        EXTENSION_TO_LANGUAGE[ext] = lang

SUPPORTED_LANGUAGES = {"python", "javascript", "typescript", "java", "c", "cpp"}

# Patterns for files to skip
SKIP_PATTERNS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
    ".egg-info",
    "target",
    ".gradle",
    "vendor",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    "*.min.js",
    "*.bundle.js",
}


def detect_language(file_path: str) -> str | None:
    """Detect language of a single file by extension."""
    ext = Path(file_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext)


def is_skipped(file_path: str) -> bool:
    """Check if file should be skipped based on path patterns."""
    path_parts = Path(file_path).parts
    for part in path_parts:
        if part in SKIP_PATTERNS:
            return True
    name = Path(file_path).name
    if name.endswith(".min.js") or name.endswith(".bundle.js"):
        return True
    return False


def collect_target_files(
    root_path: str,
    target_languages: set[str] | None = None,
) -> list[str]:
    """Collect all files in root_path that match supported languages."""
    if target_languages is None:
        target_languages = SUPPORTED_LANGUAGES

    files = []
    root = Path(root_path)
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        rel_path = str(f.relative_to(root))
        if is_skipped(rel_path):
            continue
        lang = detect_language(rel_path)
        if lang and lang in target_languages:
            files.append(rel_path)

    return sorted(files)


def detect_project_language(files: list[str]) -> str:
    """Detect the primary language of a project based on file count."""
    counts: dict[str, int] = {}
    for f in files:
        lang = detect_language(f)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return "unknown"
    return max(counts, key=counts.get)
