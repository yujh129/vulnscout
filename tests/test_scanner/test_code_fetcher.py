import os, tempfile
from vulnscout.scanner.code_fetcher import CodeFetcher, CodeFetchError

def test_fetch_local_valid_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        fetcher = CodeFetcher()
        result = fetcher.fetch_local(tmpdir)
        assert result.exists()
        assert result.is_dir()

def test_fetch_local_nonexistent():
    fetcher = CodeFetcher()
    try:
        fetcher.fetch_local("/nonexistent/path")
        assert False
    except CodeFetchError:
        pass
