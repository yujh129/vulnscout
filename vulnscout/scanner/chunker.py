from __future__ import annotations

from pathlib import Path

from vulnscout.core.config import settings

try:
    import tree_sitter_python as tspython
    import tree_sitter_java as tsjava
    from tree_sitter import Language, Parser

    _HAS_TS = True
except ImportError:
    _HAS_TS = False


_LANGUAGES: dict[str, Language] = {}

if _HAS_TS:
    try:
        _LANGUAGES["python"] = Language(tspython.language())
    except Exception:
        pass
    try:
        _LANGUAGES["java"] = Language(tsjava.language())
    except Exception:
        pass


class Chunk:
    """A single code chunk to be analyzed."""

    def __init__(self, file_path: str, code: str, line_start: int, line_end: int):
        self.file_path = file_path
        self.code = code
        self.line_start = line_start
        self.line_end = line_end

    def __repr__(self):
        return f"Chunk({self.file_path}:{self.line_start}-{self.line_end})"


def chunk_file(file_path: str, language: str) -> list[Chunk]:
    """Chunk a file into atomic analysis units (functions/methods)."""
    root_path = settings.get("scan_root", ".")
    full_path = Path(root_path) / file_path

    if not full_path.exists():
        return []

    code = full_path.read_text(encoding="utf-8", errors="replace")

    # Try AST-based chunking first
    if _HAS_TS and language in _LANGUAGES:
        return _ast_chunk(file_path, code, language)

    # Fallback: line-based chunking (max 50 lines per chunk)
    return _line_chunk(file_path, code)


def _ast_chunk(file_path: str, code: str, language: str) -> list[Chunk]:
    """Chunk using tree-sitter AST (function/method level)."""
    parser = Parser()
    parser.set_language(_LANGUAGES[language])

    tree = parser.parse(code.encode("utf-8"))
    root = tree.root_node

    chunks = []
    _extract_functions(root, code, file_path, chunks)

    if not chunks:
        lines = code.split("\n")
        chunks.append(Chunk(file_path, code, 1, len(lines)))

    return chunks


def _extract_functions(node, code: str, file_path: str, chunks: list[Chunk]):
    """Recursively extract function/method definitions from AST."""
    function_types = {
        "function_definition",
        "method_declaration",
        "function_declaration",
        "arrow_function",
    }

    if node.type in function_types:
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        lines = code.split("\n")
        chunk_code = "\n".join(lines[node.start_point[0]:node.end_point[0] + 1])
        chunks.append(Chunk(file_path, chunk_code, start_line, end_line))

    for child in node.children:
        _extract_functions(child, code, file_path, chunks)


def _line_chunk(file_path: str, code: str, max_lines: int = 50) -> list[Chunk]:
    """Fallback: chunk by line count."""
    lines = code.split("\n")
    chunks = []
    for i in range(0, len(lines), max_lines):
        chunk_lines = lines[i:i + max_lines]
        chunks.append(
            Chunk(file_path, "\n".join(chunk_lines), i + 1, i + len(chunk_lines))
        )
    return chunks
