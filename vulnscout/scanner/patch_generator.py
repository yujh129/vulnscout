from __future__ import annotations

import difflib

def generate_diff(original_code: str, fixed_code: str, file_path: str) -> str:
    original_lines = original_code.splitlines(keepends=True)
    fixed_lines = fixed_code.splitlines(keepends=True)
    diff = difflib.unified_diff(original_lines, fixed_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}")
    return "".join(diff)
