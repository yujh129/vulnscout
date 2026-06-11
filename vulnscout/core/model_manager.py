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
    try:
        resp = httpx.request(method, f"{settings.ollama_api_url}{path}", json=json_data, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _fetch_cloud_models(base_url: str, api_key: str) -> list[str]:
    """
    Query the OpenAI-compatible /models endpoint and return actual model IDs.
    Returns an empty list if unreachable or invalid.
    """
    if not api_key:
        return []
    try:
        resp = httpx.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5.0,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        # OpenAI format: { "data": [{ "id": "gpt-4o", ... }, ...] }
        models = data.get("data", [])
        if isinstance(models, list):
            return [m.get("id", "") for m in models if m.get("id")]
        return []
    except Exception:
        return []


# Known models catalog (used for metadata, actual availability is checked dynamically)
KNOWN_OLLAMA_MODELS = [
    {"name": "deepseek-coder:1.3b", "size_gb": 0.8, "description": "1.3B params, fast (8GB+ VRAM)"},
    {"name": "deepseek-coder:6.7b", "size_gb": 4.1, "description": "6.7B params, more accurate (24GB+ VRAM)"},
    {"name": "deepseek-coder:33b", "size_gb": 20.0, "description": "33B params, most accurate (48GB+ VRAM)"},
    {"name": "codellama:7b", "size_gb": 3.8, "description": "Code Llama 7B"},
    {"name": "codellama:13b", "size_gb": 7.3, "description": "Code Llama 13B"},
    {"name": "llama3:8b", "size_gb": 4.7, "description": "Meta Llama 3 8B"},
    {"name": "qwen2.5-coder:7b", "size_gb": 4.7, "description": "Qwen 2.5 Coder 7B"},
    {"name": "mistral:7b", "size_gb": 4.1, "description": "Mistral 7B"},
]

# Cloud model metadata catalog (used for lookups, actual availability is from the API)
CLOUD_MODEL_METADATA: dict[str, dict] = {
    # OpenAI
    "gpt-4o":                {"size_gb": 0, "description": "OpenAI GPT-4o"},
    "gpt-4o-mini":           {"size_gb": 0, "description": "OpenAI GPT-4o-mini, fast & cheap"},
    "gpt-4-turbo":           {"size_gb": 0, "description": "OpenAI GPT-4 Turbo"},
    "gpt-4":                 {"size_gb": 0, "description": "OpenAI GPT-4"},
    "gpt-3.5-turbo":         {"size_gb": 0, "description": "OpenAI GPT-3.5 Turbo"},
    # DeepSeek
    "deepseek-chat":         {"size_gb": 0, "description": "DeepSeek-V2 Chat"},
    "deepseek-reasoner":     {"size_gb": 0, "description": "DeepSeek-R1"},
    "deepseek-coder":        {"size_gb": 0, "description": "DeepSeek Coder"},
    "deepseek-v4-flash":     {"size_gb": 0, "description": "DeepSeek V4 Flash"},
    "deepseek-v4-pro":       {"size_gb": 0, "description": "DeepSeek V4 Pro"},
    # Anthropic
    "claude-3-opus-20240229":   {"size_gb": 0, "description": "Anthropic Claude 3 Opus"},
    "claude-3-sonnet-20240229": {"size_gb": 0, "description": "Anthropic Claude 3 Sonnet"},
    "claude-3-haiku-20240307":  {"size_gb": 0, "description": "Anthropic Claude 3 Haiku"},
}

KNOWN_CLOUD_MODELS = [
    {"name": name, **meta}
    for name, meta in CLOUD_MODEL_METADATA.items()
]


class ModelManager:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._ollama_auto_started = False
        self._cloud_models_cache: dict[str, tuple[list[str], float]] = {}  # base_url -> (model_ids, timestamp)

    def resolve_model(self, model_name: str | None = None) -> str:
        if model_name:
            return model_name
        hw = detect_hardware()
        return hw.recommended_model

    def is_ollama_installed(self) -> bool:
        return shutil.which("ollama") is not None

    def is_ollama_running(self) -> bool:
        return _ollama_api("/api/tags") is not None

    def is_downloaded(self, model_name: str) -> bool:
        try:
            tags = _ollama_api("/api/tags")
            if not tags:
                return False
            return any(model_name in m.get("name", "") for m in tags.get("models", []))
        except Exception:
            return False

    def ensure_ollama(self) -> None:
        if self.is_ollama_running():
            return
        if self.is_ollama_installed():
            self._process = subprocess.Popen(
                ["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self._ollama_auto_started = True
            for _ in range(30):
                time.sleep(0.5)
                if self.is_ollama_running():
                    return
            raise ModelError("Ollama server failed to start.")
        raise ModelError("Ollama is not reachable.")

    def download_model(
        self, model_name: str | None = None, use_mirror: bool = False, progress_callback=None
    ) -> str:
        model_tag = self.resolve_model(model_name)
        self.ensure_ollama()
        if self.is_downloaded(model_tag):
            if progress_callback:
                progress_callback(f"Model already downloaded: {model_tag}")
            return model_tag
        if progress_callback:
            progress_callback(f"Pulling {model_tag} via Ollama...")
        if self.is_ollama_installed():
            result = subprocess.run(
                ["ollama", "pull", model_tag]
            )
            if result.returncode != 0:
                raise ModelError(f"Failed to pull model.")
        else:
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
        if self._process and self._ollama_auto_started:
            self._process.terminate()
            self._process = None
            self._ollama_auto_started = False

    # ------------------------------------------------------------------ #
    #  Dynamic model detection
    # ------------------------------------------------------------------ #

    def _ollama_available(self) -> bool:
        """Check if Ollama server is reachable (fast, no side effects)."""
        return self.is_ollama_running()

    def _get_cloud_models(self) -> list[str]:
        """Fetch actual model IDs from the cloud API endpoint. Cached for 60s."""
        import time as _time

        now = _time.time()
        cache_key = settings.openai_base_url
        cached = self._cloud_models_cache.get(cache_key)
        if cached and (now - cached[1]) < 60:
            return cached[0]

        if not settings.openai_api_key:
            self._cloud_models_cache[cache_key] = ([], now)
            return []

        model_ids = _fetch_cloud_models(settings.openai_base_url, settings.openai_api_key)
        self._cloud_models_cache[cache_key] = (model_ids, now)
        return model_ids

    def get_actually_available_models(self) -> dict:
        """
        Dynamically detect which models are actually available right now.

        Returns a dict:
        {
            "local": [...],   # Ollama models that are downloaded
            "cloud": [...],   # Cloud models (only if API key is valid)
            "downloadable": [...],  # Ollama models available to pull (not yet downloaded)
            "ollama_running": bool,
            "ollama_installed": bool,
            "cloud_configured": bool,
        }
        """
        result = {
            "local": [],
            "cloud": [],
            "downloadable": [],
            "ollama_running": False,
            "ollama_installed": False,
            "cloud_configured": False,
        }

        # Check Ollama
        ollama_running = self._ollama_available()
        result["ollama_running"] = ollama_running
        result["ollama_installed"] = self.is_ollama_installed()

        if ollama_running:
            downloaded_names = self.list_downloaded_models()
            for m in KNOWN_OLLAMA_MODELS:
                entry = {**m, "provider": "ollama"}
                if m["name"] in downloaded_names:
                    entry["downloaded"] = True
                    result["local"].append(entry)
                else:
                    entry["downloaded"] = False
                    result["downloadable"].append(entry)

            # Also include any downloaded models not in our known list (user-installed)
            for dname in downloaded_names:
                if not any(dname == km["name"] for km in KNOWN_OLLAMA_MODELS):
                    result["local"].append({
                        "name": dname,
                        "size_gb": 0,
                        "description": "User-installed model",
                        "provider": "ollama",
                        "downloaded": True,
                    })

        # Check Cloud API — fetch actual models from the endpoint
        cloud_model_ids = self._get_cloud_models()
        result["cloud_configured"] = len(cloud_model_ids) > 0
        for mid in cloud_model_ids:
            meta = CLOUD_MODEL_METADATA.get(mid, {"size_gb": 0, "description": "Available via API"})
            entry = {"name": mid, **meta, "provider": "openai"}
            result["cloud"].append(entry)

        return result

    def list_available_models(self) -> list[dict]:
        """Legacy method: return all known models with metadata (no dynamic check)."""
        result = []
        for m in KNOWN_OLLAMA_MODELS:
            result.append({**m, "provider": "ollama"})
        for m in KNOWN_CLOUD_MODELS:
            result.append({**m, "provider": "openai"})
        return result

    def list_downloaded_models(self) -> list[str]:
        try:
            tags = _ollama_api("/api/tags")
            if not tags:
                return []
            return [m.get("name", "") for m in tags.get("models", [])]
        except Exception:
            return []
