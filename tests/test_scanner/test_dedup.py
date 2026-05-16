from vulnscout.scanner.dedup import deduplicate, sort_by_severity


def test_dedup_removes_duplicate_cwe():
    findings = [
        {"file_path": "a.py", "cwe_id": "CWE-89", "severity": "critical", "title": "SQLi"},
        {"file_path": "a.py", "cwe_id": "CWE-89", "severity": "critical", "title": "SQLi"},
    ]
    result = deduplicate(findings)
    assert len(result) == 1


def test_dedup_keeps_different_cwe():
    findings = [
        {"file_path": "a.py", "cwe_id": "CWE-89", "severity": "critical", "title": "SQLi"},
        {"file_path": "a.py", "cwe_id": "CWE-79", "severity": "high", "title": "XSS"},
    ]
    result = deduplicate(findings)
    assert len(result) == 2


def test_sort_by_severity():
    findings = [
        {"severity": "low", "title": "Low"},
        {"severity": "critical", "title": "Critical"},
        {"severity": "medium", "title": "Medium"},
        {"severity": "high", "title": "High"},
    ]
    result = sort_by_severity(findings)
    assert result[0]["severity"] == "critical"
    assert result[1]["severity"] == "high"
    assert result[2]["severity"] == "medium"
    assert result[3]["severity"] == "low"
