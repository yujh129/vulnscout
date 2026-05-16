from vulnscout.scanner.language_detector import (
    detect_language,
    is_skipped,
    collect_target_files,
    detect_project_language,
)


def test_detect_language_python():
    assert detect_language("main.py") == "python"
    assert detect_language("module/__init__.py") == "python"


def test_detect_language_javascript():
    assert detect_language("app.js") == "javascript"
    assert detect_language("component.jsx") == "javascript"


def test_detect_language_java():
    assert detect_language("Main.java") == "java"


def test_detect_language_unknown():
    assert detect_language("readme.md") is None
    assert detect_language("data.json") is None


def test_is_skipped_node_modules():
    assert is_skipped("node_modules/package/index.js") is True


def test_is_skipped_git():
    assert is_skipped(".git/objects/abc123") is True


def test_is_skipped_normal_file():
    assert is_skipped("src/main.py") is False


def test_collect_target_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.js").write_text("const x = 1;")
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("module.exports = {};")

    files = collect_target_files(str(tmp_path), {"python", "javascript"})
    assert "src/main.py" in files
    assert "src/utils.js" in files
    assert "README.md" not in files
    assert "node_modules/dep.js" not in files


def test_detect_project_language():
    files = ["a.py", "b.py", "c.js", "d.java"]
    assert detect_project_language(files) == "python"
