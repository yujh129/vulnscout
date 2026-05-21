from vulnscout.scanner.language_detector import detect_language, is_skipped, collect_target_files, detect_project_language

def test_detect_language_python():
    assert detect_language("main.py") == "python"

def test_detect_language_unknown():
    assert detect_language("readme.md") is None

def test_is_skipped_node_modules():
    assert is_skipped("node_modules/package/index.js") is True

def test_is_skipped_normal_file():
    assert is_skipped("src/main.py") is False

def test_detect_project_language():
    assert detect_project_language(["a.py", "b.py", "c.js"]) == "python"
