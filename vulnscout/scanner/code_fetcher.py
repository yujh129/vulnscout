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

    def fetch_zip(self, zip_data: bytes) -> Path:
        dest = self.work_dir / "source"
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(dest)
        return dest

    def fetch_github(self, repo_url: str, depth: int = 1) -> Path:
        import git
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        dest = self.work_dir / repo_name
        if dest.exists():
            shutil.rmtree(dest)
        try:
            git.Repo.clone_from(repo_url, str(dest), depth=depth)
        except git.GitCommandError as e:
            raise CodeFetchError(f"Git clone failed: {e}")
        return dest

    def cleanup(self):
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)
