from __future__ import annotations
import asyncio
import traceback
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from vulnscout.models.db import get_db, SessionLocal
from vulnscout.models.schemas import Patch, PatchStatus, Scan, ScanResponse, ScanStatus, SourceType, Vulnerability, VulnerabilityResponse, PatchResponse
from vulnscout.scanner.code_fetcher import CodeFetcher
from vulnscout.scanner.pipeline import ScanPipeline
from vulnscout.scanner.analyzer import Analyzer
from vulnscout.scanner.patch_generator import generate_diff
from vulnscout.scanner.language_detector import detect_language
from vulnscout.utils.report_formatter import format_report
router = APIRouter()


def _run_scan_background(scan_id: str, source_dir: str) -> None:
    """Run the scan pipeline in a background thread."""
    from vulnscout.api.ws import broadcast_progress

    class WsProgress:
        def on_progress(self, percent, current_file=None):
            from asyncio import get_event_loop
            try:
                loop = get_event_loop()
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(
                        broadcast_progress(scan_id, {
                            "type": "progress", "percent": percent,
                            "current_file": current_file
                        })
                    )
                )
            except Exception:
                pass

        def on_vuln_found(self, file, severity, title):
            from asyncio import get_event_loop
            try:
                loop = get_event_loop()
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(
                        broadcast_progress(scan_id, {
                            "type": "vuln_found", "file": file,
                            "severity": severity, "title": title
                        })
                    )
                )
            except Exception:
                pass

        def on_file_done(self, file, vuln_count):
            pass

        def on_scan_done(self, total_vulns, duration):
            from asyncio import get_event_loop
            try:
                loop = get_event_loop()
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(
                        broadcast_progress(scan_id, {
                            "type": "scan_done",
                            "total_vulns": total_vulns,
                            "duration": duration
                        })
                    )
                )
            except Exception:
                pass

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return
        pipeline = ScanPipeline(db, progress=WsProgress())
        pipeline.run(scan, source_dir)
    except Exception:
        traceback.print_exc()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = ScanStatus.FAILED
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("", response_model=ScanResponse)
async def create_scan(
    background_tasks: BackgroundTasks,
    source_type: str = "local",
    source_path: str = "",
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    scan = Scan(
        source_type=source_type,
        source_path=source_path or "upload",
        status=ScanStatus.PENDING,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    fetcher = CodeFetcher()
    try:
        if source_type == SourceType.URL:
            source_dir = str(fetcher.fetch_github(source_path))
        elif file:
            zip_data = await file.read()
            source_dir = str(fetcher.fetch_zip(zip_data))
            scan.source_path = file.filename or "upload.zip"
        else:
            source_dir = source_path
            if not Path(source_path).exists():
                raise HTTPException(status_code=400, detail=f"Path not found: {source_path}")
    except Exception as e:
        scan.status = ScanStatus.FAILED
        db.commit()
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()

    # Run scan in background — response returns immediately
    asyncio.get_event_loop().run_in_executor(
        None, _run_scan_background, scan.id, source_dir
    )

    return ScanResponse.model_validate(scan)

@router.get("", response_model=list[ScanResponse])
async def list_scans(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    return [ScanResponse.model_validate(s) for s in scans]

@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    percent = (scan.scanned_files / scan.total_files * 100) if scan.total_files > 0 else 100
    resp = ScanResponse.model_validate(scan)
    resp.progress_percent = percent
    return resp

@router.get("/{scan_id}/results", response_model=list[VulnerabilityResponse])
async def get_results(scan_id: str, severity: str | None = None, file_path: str | None = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id)
    if severity:
        query = query.filter(Vulnerability.severity == severity)
    if file_path:
        query = query.filter(Vulnerability.file_path == file_path)
    vulns = query.offset(skip).limit(limit).all()
    return [VulnerabilityResponse.model_validate(v) for v in vulns]

@router.get("/{scan_id}/results/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(scan_id: str, vuln_id: str, db: Session = Depends(get_db)):
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id, Vulnerability.scan_id == scan_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return VulnerabilityResponse.model_validate(vuln)

@router.get("/{scan_id}/results/{vuln_id}/patches", response_model=list[PatchResponse])
async def get_patches(scan_id: str, vuln_id: str, db: Session = Depends(get_db)):
    patches = db.query(Patch).join(Vulnerability).filter(Vulnerability.id == vuln_id, Vulnerability.scan_id == scan_id).all()
    return [PatchResponse.model_validate(p) for p in patches]

@router.get("/{scan_id}/report")
async def download_report(scan_id: str, format: str = "json", db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).all()
    content, media_type = format_report(scan, vulns, format)
    return Response(content=content, media_type=media_type)


@router.post("/{scan_id}/patches/generate")
async def generate_patches(scan_id: str, db: Session = Depends(get_db)):
    """Generate fix patches for all vulnerabilities in a completed scan."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != ScanStatus.DONE:
        raise HTTPException(status_code=400, detail="Scan is not completed yet")

    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).all()
    if not vulns:
        raise HTTPException(status_code=400, detail="No vulnerabilities found in this scan")

    analyzer = Analyzer()
    if not analyzer._check_model():
        raise HTTPException(status_code=400, detail="AI model not available. Check model configuration.")

    generated = 0
    errors = 0
    for vuln in vulns:
        existing = db.query(Patch).filter(Patch.vuln_id == vuln.id).first()
        if existing:
            continue
        try:
            code = vuln.vulnerable_code or ""
            if not code.strip():
                errors += 1
                continue
            lang = detect_language(vuln.file_path) or "python"
            fixed_code = analyzer.generate_fix(code, {
                "title": vuln.title or "",
                "cwe_id": vuln.cwe_id or "",
                "description": vuln.description or "",
                "line_start": vuln.line_start or 1,
                "line_end": vuln.line_end or 1,
            }, lang)
            if fixed_code:
                diff = generate_diff(code, fixed_code, vuln.file_path)
                db.add(Patch(vuln_id=vuln.id, diff_content=diff,
                    description=f"Auto-generated fix for {vuln.title}", status=PatchStatus.DRAFT))
                generated += 1
            else:
                errors += 1
        except Exception:
            errors += 1
        db.commit()

    return {"scan_id": scan_id, "generated": generated, "errors": errors}
