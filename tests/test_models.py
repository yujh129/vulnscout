from vulnscout.models.schemas import Scan, ScanStatus, SourceType, Vulnerability

def test_create_scan(db_session):
    scan = Scan(source_type=SourceType.LOCAL, source_path="/tmp/test")
    db_session.add(scan)
    db_session.commit()
    saved = db_session.query(Scan).first()
    assert saved is not None
    assert saved.status == ScanStatus.PENDING

def test_create_vulnerability(db_session):
    scan = Scan(source_type=SourceType.LOCAL, source_path="/tmp/test")
    db_session.add(scan)
    db_session.commit()
    vuln = Vulnerability(scan_id=scan.id, file_path="app.py", line_start=10, line_end=20, cwe_id="CWE-89", severity="high", title="SQL Injection")
    db_session.add(vuln)
    db_session.commit()
    saved = db_session.query(Vulnerability).first()
    assert saved.cwe_id == "CWE-89"
