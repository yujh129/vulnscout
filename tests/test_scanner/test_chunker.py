from vulnscout.scanner.chunker import _line_chunk, Chunk

def test_line_chunk_small_file():
    chunks = _line_chunk("test.py", "line1\nline2\nline3", max_lines=2)
    assert len(chunks) >= 1
    assert all(isinstance(c, Chunk) for c in chunks)

def test_line_chunk_respects_max_lines():
    code = "\n".join(f"line{i}" for i in range(100))
    chunks = _line_chunk("test.py", code, max_lines=30)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.code.count("\n") + 1 <= 30
