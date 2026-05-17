from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import httpx

from vulnscout.core.config import settings
from vulnscout.core.detector import detect_hardware


class ModelError(Exception):
    pass


def _ollama_api(path: str, method: str = "GET", json_data: dict | None = None, timeout: float = 5.0) -> dict | None:
    """Call Ollama API and return JSON response, or None on failure."""
    try:
        resp = httpx.request(
            method,
            f"{settings.ollama_api_url}{path}",
            json=json_data,
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


class ModelManager:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._ollama_auto_started = False

    def resolve_model(self, model_name: str | None = None) -> str:
        """Return the Ollama model tag to use."""
        if model_name:
            return model_name
        hw = detect_hardware()
        return hw.recommended_model

    def is_ollama_installed(self) -> bool:
        """Check if Ollama CLI is available."""
        return shutil.which("ollama") is not None

    def is_ollama_running(self) -> bool:
        """Check if Ollama server is running by hitting its API."""
        return _ollama_api("/api/tags") is not None

    def is_downloaded(self, model_name: str) -> bool:
        """Check if model is already pulled in Ollama."""
        try:
            tags = _ollama_api("/api/tags")
            if not tags:
                return False
            models = tags.get("models", [])
            return any(model_name in m.get("name", "") for m in models)
        except Exception:
            return False

    def ensure_ollama(self) -> None:
        """Ensure Ollama is reachable. Handles both local and remote (Docker) setups."""
        # If API is already reachable (remote Ollama via env var), we're good
        if self.is_ollama_running():
            return

        # If CLI is installed, auto-start it locally
        if self.is_ollama_installed():
            self._process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._ollama_auto_started = True
            for _ in range(30):
                time.sleep(0.5)
                if self.is_ollama_running():
                    return
            raise ModelError("Ollama server failed to start. Try running 'ollama serve' manually.")

        # Neither API nor CLI available
        raise ModelError(
            "Ollama is not reachable.\n"
            "  Local: curl -fsSL https://ollama.com/install.sh | sh\n"
            "  Docker: Ensure the ollama service is running (docker compose up -d ollama)"
        )

    def download_model(
        self,
        model_name: str | None = None,
        use_mirror: bool = False,
        progress_callback=None,
    ) -> str:
        """Pull an Ollama model. Uses CLI if available, otherwise HTTP API.

        Returns the model tag (e.g. 'deepseek-coder:1.3b').
        """
        model_tag = self.resolve_model(model_name)
        self.ensure_ollama()

        if self.is_downloaded(model_tag):
            if progress_callback:
                progress_callback(f"Model already downloaded: {model_tag}")
            return model_tag

        if progress_callback:
            progress_callback(f"Pulling {model_tag} via Ollama...")

        # Prefer CLI if available (local install)
        if self.is_ollama_installed():
            try:
                result = subprocess.run(
                    ["ollama", "pull", model_tag],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode != 0:
                    raise ModelError(f"Failed to pull model: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                raise ModelError("Model download timed out.")
        else:
            # Fallback: use Ollama HTTP API (works with remote Ollama in Docker)
            try:
                with httpx.stream(
                    "POST",
                    f"{settings.ollama_api_url}/api/pull",
                    json={"name": model_tag},
                    timeout=600,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            if data.get("status") == "success":
                                break
            except Exception as e:
                raise ModelError(f"Failed to pull model via API: {e}")

        if progress_callback:
            progress_callback(f"Model ready: {model_tag}")

        return model_tag

    def stop_backend(self):
        """Stop auto-started Ollama process, if any."""
        if self._process and self._ollama_auto_started:
            self._process.terminate()
            self._process = None
            self._ollama_auto_started = False

    def list_available_models(self) -> list[dict]:
        """Return list of recommended models for this project."""
        return [
            {"name": "deepseek-coder:1.3b", "size_gb": 0.8, "description": "1.3B parameters, fast, good for most scans (8GB+ VRAM)"},
            {"name": "deepseek-coder:6.7b", "size_gb": 4.1, "description": "6.7B parameters, more accurate, requires 24GB+ VRAM"},
        ]

    def list_downloaded_models(self) -> list[str]:
        """Return list of models pulled in Ollama (filtered to relevant ones)."""
        try:
            tags = _ollama_api("/api/tags")
            if not tags:
                return []
            return [m.get("name", "") for m in tags.get("models", [])]
        except Exception:
            return []
