from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class HardwareInfo:
    has_gpu: bool = False
    gpu_count: int = 0
    total_vram_mb: int = 0
    gpu_name: str = ""
    has_ollama: bool = False
    has_llama_cpp: bool = False
    has_vllm: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def recommended_model(self) -> str:
        from vulnscout.core.model_manager import KNOWN_OLLAMA_MODELS
        if not self.has_gpu:
            return KNOWN_OLLAMA_MODELS[0]["name"] if KNOWN_OLLAMA_MODELS else "deepseek-coder:1.3b"
        vram = self.total_vram_mb
        # Pick the largest model that fits in VRAM (rough: model needs ~4x its size in VRAM)
        best = KNOWN_OLLAMA_MODELS[0]
        for m in KNOWN_OLLAMA_MODELS:
            if m["size_gb"] > 0 and m["size_gb"] * 4 * 1024 <= vram:
                best = m
        return best["name"]

    @property
    def recommended_backend(self) -> str:
        if self.has_ollama:
            return "ollama"
        return "ollama"


def detect_hardware() -> HardwareInfo:
    info = HardwareInfo()
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                info.gpu_count = len(lines)
                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 2:
                        info.gpu_name = parts[0]
                        info.total_vram_mb += int(parts[1])
                info.has_gpu = info.gpu_count > 0
        except Exception:
            pass
    info.has_ollama = shutil.which("ollama") is not None
    if shutil.which("llama-cpp-server") or _import_check("llama_cpp"):
        info.has_llama_cpp = True
    if _import_check("vllm"):
        info.has_vllm = True
    if not info.has_gpu:
        info.warnings.append("No NVIDIA GPU detected. Using CPU mode (Ollama).")
    if not info.has_ollama:
        info.warnings.append("Ollama not found. Install: curl -fsSL https://ollama.com/install.sh | sh")
    return info

def _import_check(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False
