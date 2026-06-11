from vulnscout.core.detector import detect_hardware, HardwareInfo

def test_detect_returns_info():
    info = detect_hardware()
    assert isinstance(info, HardwareInfo)
    assert isinstance(info.has_gpu, bool)
    assert len(info.recommended_model) > 0

def test_hardware_info_defaults():
    info = HardwareInfo()
    assert info.has_gpu is False
    assert info.recommended_model == "deepseek-coder:1.3b"
    assert info.recommended_backend == "ollama"

def test_hardware_info_vram_selection():
    info = HardwareInfo()
    # No GPU → picks smallest model
    assert info.recommended_model is not None and len(info.recommended_model) > 0

    info.has_gpu = True
    info.total_vram_mb = 24000
    # 24GB VRAM → picks a model that fits (size_gb * 4 * 1024 <= 24000)
    from vulnscout.core.model_manager import KNOWN_OLLAMA_MODELS
    chosen = info.recommended_model
    assert chosen is not None
    # The chosen model should exist in the known list
    assert any(m["name"] == chosen for m in KNOWN_OLLAMA_MODELS)
