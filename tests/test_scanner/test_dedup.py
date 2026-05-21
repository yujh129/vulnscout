from vulnscout.scanner.dedup import deduplicate, sort_by_severity

def test_dedup_removes_duplicate_cwe():
    findings = [{"file_path": "a.py", "cwe_id": "CWE-89", "severity": "critical", "title": "SQLi"},
                {"file_path": "a.py", "cwe_id": "CWE-89", "severity": "critical", "title": "SQLi"}]
    assert len(deduplicate(findings)) == 1

def test_dedup_keeps_different_cwe():
    findings = [{"file_path": "a.py", "cwe_id": "CWE-89", "severity": "critical", "title": "SQLi"},
                {"file_path": "a.py", "cwe_id": "CWE-79", "severity": "high", "title": "XSS"}]
    assert len(deduplicate(findings)) == 2

def test_sort_by_severity():
    findings = [{"severity": "low"}, {"severity": "critical"}, {"severity": "medium"}, {"severity": "high"}]
    result = sort_by_severity(findings)
    assert result[0]["severity"] == "critical"
    assert result[3]["severity"] == "low"
