from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from vulnscout.models.db import get_db
from vulnscout.models.schemas import (
    Patch,
    Scan,
    ScanCreate,
    ScanResponse,
    ScanStatus,
    SourceType,
    Vulnerability,
    VulnerabilityResponse,
    PatchResponse,
)
from vulnscout.scanner.code_fetcher import CodeFetcher
from vulnscout.scanner.pipeline import ScanPipeline
from vulnscout.utils.report_formatter import format_report

router = APIRouter()


@router.post("", response_model=ScanResponse)
async def create_scan(
    source_type: str = "local",
    source_path: str = "",
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Create a new scan."""
    scan = Scan(source_type=source_type, source_path=source_path or "upload")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Resolve source
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
        raise HTTPException(status_code=400, detail=str(e))

    # Run pipeline
    pipeline = ScanPipeline(db)
    try:
        pipeline.run(scan, source_dir)
    except Exception as e:
        scan.status = ScanStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}")
    finally:
        fetcher.cleanup()

    return ScanResponse.model_validate(scan)


@router.get("", response_model=list[ScanResponse])
async def list_scans(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List all scans."""
    scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    return [ScanResponse.model_validate(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, db: Session = Depends(get_db)):
    """Get scan status and summary."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    percent = (scan.scanned_files / scan.total_files * 100) if scan.total_files > 0 else 100

    resp = ScanResponse.model_validate(scan)
    resp.progress_percent = percent
    return resp


@router.get("/{scan_id}/results", response_model=list[VulnerabilityResponse])
async def get_results(
    scan_id: str,
    severity: str | None = None,
    file_path: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get vulnerabilities for a scan."""
    query = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id)
    if severity:
        query = query.filter(Vulnerability.severity == severity)
    if file_path:
        query = query.filter(Vulnerability.file_path == file_path)
    vulns = query.offset(skip).limit(limit).all()
    return [VulnerabilityResponse.model_validate(v) for v in vulns]


@router.get("/{scan_id}/results/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(scan_id: str, vuln_id: str, db: Session = Depends(get_db)):
    """Get single vulnerability detail."""
    vuln = (
        db.query(Vulnerability)
        .filter(Vulnerability.id == vuln_id, Vulnerability.scan_id == scan_id)
        .first()
    )
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return VulnerabilityResponse.model_validate(vuln)


@router.get("/{scan_id}/results/{vuln_id}/patches", response_model=list[PatchResponse])
async def get_patches(scan_id: str, vuln_id: str, db: Session = Depends(get_db)):
    """Get patches for a vulnerability."""
    patches = (
        db.query(Patch)
        .join(Vulnerability)
        .filter(Vulnerability.id == vuln_id, Vulnerability.scan_id == scan_id)
        .all()
    )
    return [PatchResponse.model_validate(p) for p in patches]


@router.get("/{scan_id}/report")
async def download_report(scan_id: str, format: str = "json", db: Session = Depends(get_db)):
    """Download scan report."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).all()

    content, media_type = format_report(scan, vulns, format)
    return Response(content=content, media_type=media_type)
