from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from pathlib import Path

class CodeFetchError(Exception):
    pass

class CodeFetcher:
    def __init__(self, work_dir: str | None = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="vulnscout_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def fetch_local(self, path: str) -> Path:
        src = Path(path).resolve()
        if not src.exists():
            raise CodeFetchError(f"Path does not exist: {path}")
        if not src.is_dir():
            raise CodeFetchError(f"Path is not a directory: {path}")
        return src

    def fetch_zip(self, zip_data: bytes, extract_dir: str = "source") -> Path:
        dest = self.work_dir / extract_dir
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(dest)
        return dest

    def fetch_github(self, repo_url: str, depth: int = 1) -> Path:
        import git
        import re

        # Normalize GitHub URL to a cloneable format.
        # Supports:
        #   https://github.com/owner/repo
        #   https://github.com/owner/repo.git
        #   https://github.com/owner/repo/tree/branch
        #   https://github.com/owner/repo/tree/branch/path
        #   https://github.com/owner/repo/blob/branch/file
        #   git@github.com:owner/repo.git

        url = repo_url.rstrip("/")

        # Extract owner and repo name only (ignore /tree/... /blob/... paths)
        match = re.match(
            r"(?:https://github\.com/|git@github\.com:)([^/]+)/([^/#?]+)(?:\.git)?",
            url,
        )
        if not match:
            raise CodeFetchError(
                f"Invalid GitHub URL: {repo_url}. "
                "Expected format: https://github.com/owner/repo"
            )

        owner = match.group(1)
        repo = match.group(2).replace(".git", "")

        clone_url = f"https://github.com/{owner}/{repo}.git"
        dest = self.work_dir / repo
        if dest.exists():
            shutil.rmtree(dest)
        try:
            git.Repo.clone_from(clone_url, str(dest), depth=depth)
        except git.GitCommandError as e:
            raise CodeFetchError(f"Git clone failed: {e}")
        return dest

    def cleanup(self):
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)
