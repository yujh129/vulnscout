from __future__ import annotations

import difflib


def generate_diff(original_code: str, fixed_code: str, file_path: str) -> str:
    """Generate a unified diff between original and fixed code."""
    original_lines = original_code.splitlines(keepends=True)
    fixed_lines = fixed_code.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    )
    return "".join(diff)


def apply_patch(original_code: str, diff_content: str) -> str | None:
    """Apply a unified diff to original code. Returns patched code or None on failure."""
    # For MVP, display the diff for manual application.
    # Future: integrate with git apply or a patch library.
    return None
