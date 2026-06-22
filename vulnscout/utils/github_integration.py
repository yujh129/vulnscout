from __future__ import annotations
import base64
import re
import httpx
from vulnscout.core.config import settings


class GitHubError(Exception):
    pass


def _parse_repo(source_path: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL or fail with GitHubError."""
    m = re.match(
        r"(?:https://github\.com/|git@github\.com:)([^/]+)/([^/.]+)", source_path
    )
    if m:
        return m.group(1), m.group(2)
    raise GitHubError(
        f"Cannot parse GitHub repo from: {source_path}. "
        f"Make sure the scan source is a valid GitHub repository URL."
    )


def _headers() -> dict:
    if not settings.github_token:
        raise GitHubError("GitHub token not configured. Set GITHUB_TOKEN in .env")
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _api(path: str, method: str = "GET", json_data: dict | None = None) -> dict:
    try:
        resp = httpx.request(
            method,
            f"https://api.github.com{path}",
            headers=_headers(),
            json=json_data,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        raise GitHubError(
            f"GitHub API error ({resp.status_code}): {resp.text[:200]}"
        )
    except httpx.RequestError as e:
        raise GitHubError(f"GitHub API request failed: {e}")


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def create_issue(
    repo_path: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> dict:
    """Create a GitHub issue on the repository."""
    owner, repo = _parse_repo(repo_path)
    data: dict = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    return _api(f"/repos/{owner}/{repo}/issues", method="POST", json_data=data)


def create_pr(
    repo_path: str,
    branch_name: str,
    diff_content: str,
    commit_message: str,
    pr_title: str,
    pr_body: str,
    base_branch: str = "main",
) -> dict:
    """Create a GitHub pull request with file changes from unified diffs.

    When multiple diffs target the same file only the first one is applied
    (to avoid conflicting fixes overwriting each other).
    """
    owner, repo = _parse_repo(repo_path)

    # 1. Resolve the base-branch SHA
    ref_data = _api(f"/repos/{owner}/{repo}/git/ref/heads/{base_branch}")
    base_sha = ref_data["object"]["sha"]

    # 2. Create a fresh branch (delete old one if it already exists)
    _ensure_branch(owner, repo, branch_name, base_sha)

    # 3. Parse diffs – first patch wins for duplicate file paths
    file_patches = _parse_diff(diff_content)

    changed_files = 0
    seen_files: set[str] = set()

    for file_path, patch_text in file_patches.items():
        if file_path in seen_files:
            continue  # deduplicate: use only first patch per file
        seen_files.add(file_path)

        # Get original file content from the base branch
        try:
            current = _api(
                f"/repos/{owner}/{repo}/contents/{file_path}?ref={base_branch}"
            )
            original_bytes = base64.b64decode(current["content"])
            original_content = original_bytes.decode("utf-8")
            current_sha = current["sha"]
        except GitHubError:
            # File does not exist in base – treat as new-file creation
            original_content = ""
            current_sha = None

        new_content = _apply_patch(original_content, patch_text)
        if new_content is None or new_content == original_content:
            continue

        data = {
            "message": commit_message,
            "content": base64.b64encode(new_content.encode()).decode(),
            "branch": branch_name,
        }
        if current_sha:
            data["sha"] = current_sha
        _api(
            f"/repos/{owner}/{repo}/contents/{file_path}",
            method="PUT",
            json_data=data,
        )
        changed_files += 1

    if changed_files == 0:
        raise GitHubError("No files were changed by the patches")

    # 4. Open the pull request
    return _api(
        f"/repos/{owner}/{repo}/pulls",
        method="POST",
        json_data={
            "title": pr_title,
            "head": branch_name,
            "base": base_branch,
            "body": pr_body,
        },
    )


def get_repo_info(repo_path: str) -> dict:
    """Return repository metadata from the GitHub API."""
    owner, repo = _parse_repo(repo_path)
    return _api(f"/repos/{owner}/{repo}")


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------


def _ensure_branch(owner: str, repo: str, branch_name: str, sha: str) -> None:
    """Create *branch_name* at *sha*, deleting it first if it already exists."""
    try:
        _api(f"/repos/{owner}/{repo}/git/ref/heads/{branch_name}")
        # Branch exists – delete it
        _api(
            f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
            method="DELETE",
        )
    except GitHubError:
        pass  # branch does not exist, that's fine

    _api(
        f"/repos/{owner}/{repo}/git/refs",
        method="POST",
        json_data={"ref": f"refs/heads/{branch_name}", "sha": sha},
    )


def _parse_diff(diff_content: str) -> dict[str, str]:
    """Parse concatenated unified-diff text into a {file_path: patch_hunks} map.

    When multiple diffs target the same file, only the *first* one is kept
    to avoid conflicting fixes overwriting each other.
    """
    files: dict[str, str] = {}
    current_file: str | None = None
    current_lines: list[str] = []

    for line in diff_content.split("\n"):
        if line.startswith("--- a/"):
            continue
        elif line.startswith("+++ b/"):
            if current_file is not None and current_lines and current_file not in files:
                files[current_file] = "\n".join(current_lines)
            current_file = line[6:]
            current_lines = []
        else:
            current_lines.append(line)

    if (
        current_file is not None
        and current_lines
        and current_file not in files
    ):
        files[current_file] = "\n".join(current_lines)

    return files


def _apply_patch(original_content: str, patch_text: str) -> str | None:
    """Apply a unified-diff patch onto *original_content* and return the full result.

    The patch hunks are applied using their original line-number positions.
    Lines between hunks are preserved from the original content.
    """
    if not patch_text:
        return None

    original_lines = original_content.splitlines(keepends=True)
    hunks = _parse_hunks(patch_text)
    if not hunks:
        return None

    result: list[str] = []
    orig_pos = 0  # 0-indexed position in original_lines

    for old_start, _old_count, hunk_lines in hunks:
        hunk_start = old_start - 1  # convert to 0-indexed

        # Copy lines from the original that come before this hunk
        while orig_pos < hunk_start and orig_pos < len(original_lines):
            result.append(original_lines[orig_pos])
            orig_pos += 1

        # Walk through the hunk body
        for hunk_line in hunk_lines:
            prefix = hunk_line[:1] if hunk_line else ""
            if prefix == " ":
                # Context line – keep the corresponding original line
                if orig_pos < len(original_lines):
                    result.append(original_lines[orig_pos])
                orig_pos += 1
            elif prefix == "-":
                # Removed line – skip the corresponding original line
                orig_pos += 1
            elif prefix == "+":
                # Added line – include the new content (strip the leading '+')
                result.append(hunk_line[1:])
            # Other lines (e.g. '\ No newline at end of file') are ignored

    # Copy any remaining original lines after the last hunk
    while orig_pos < len(original_lines):
        result.append(original_lines[orig_pos])
        orig_pos += 1

    return "".join(result)


def _parse_hunks(patch_text: str) -> list[tuple[int, int, list[str]]]:
    """Parse unified-diff hunks from *patch_text*.

    Returns a list of ``(old_start, old_count, hunk_lines)`` tuples.
    *old_start* is 1-indexed.
    """
    hunks: list[tuple[int, int, list[str]]] = []
    current: tuple[int, int, list[str]] | None = None

    for line in patch_text.splitlines(keepends=True):
        if line.startswith("@@"):
            if current is not None:
                hunks.append(current)
            parts = line.split()
            # parts[1] looks like '-start,count'  (or just '-start')
            old_part = parts[1][1:]  # strip leading '-'
            if "," in old_part:
                old_start_str, old_count_str = old_part.split(",", 1)
            else:
                old_start_str, old_count_str = old_part, "1"
            current = (int(old_start_str), int(old_count_str), [])
        elif current is not None:
            current[2].append(line)

    if current is not None:
        hunks.append(current)

    return hunks
