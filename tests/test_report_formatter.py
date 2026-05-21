import json
from vulnscout.models.schemas import Scan, Vulnerability
from vulnscout.utils.report_formatter import format_report

def test_format_json():
    scan = Scan(source_type="local", source_path="/test", vuln_count_high=1)
    vulns = [Vulnerability(scan_id=scan.id, file_path="app.py", line_start=10, cwe_id="CWE-89", severity="high", title="SQLi")]
    content, mt = format_report(scan, vulns, "json")
    assert mt == "application/json"
    data = json.loads(content)
    assert data["summary"]["high"] == 1

def test_format_markdown():
    scan = Scan(source_type="local", source_path="/test")
    vulns = [Vulnerability(scan_id=scan.id, file_path="app.py", cwe_id="CWE-89", severity="critical", title="SQLi")]
    content, mt = format_report(scan, vulns, "markdown")
    assert mt == "text/markdown"
    assert "VulnScout Scan Report" in content

def test_format_sarif():
    scan = Scan(source_type="local", source_path="/test")
    vulns = [Vulnerability(scan_id=scan.id, file_path="app.py", cwe_id="CWE-89", severity="critical", title="SQLi")]
    content, mt = format_report(scan, vulns, "sarif")
    assert mt == "application/json"
    data = json.loads(content)
    assert data["version"] == "2.1.0"
