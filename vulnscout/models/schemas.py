from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from vulnscout.models.db import Base


# ── Enums ──────────────────────────────────────────────────────────────

class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class SourceType(str, Enum):
    LOCAL = "local"
    URL = "url"
    CLI = "cli"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PatchStatus(str, Enum):
    DRAFT = "draft"
    APPLIED = "applied"
    REJECTED = "rejected"


# ── SQLAlchemy Models ──────────────────────────────────────────────────

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(16), default=ScanStatus.PENDING)
    source_type = Column(String(16))
    source_path = Column(Text)
    language = Column(String(32))
    total_files = Column(Integer, default=0)
    scanned_files = Column(Integer, default=0)
    vuln_count_critical = Column(Integer, default=0)
    vuln_count_high = Column(Integer, default=0)
    vuln_count_medium = Column(Integer, default=0)
    vuln_count_low = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vulnerabilities = relationship("Vulnerability", back_populates="scan", cascade="all, delete-orphan")


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String(36), ForeignKey("scans.id"), nullable=False)
    file_path = Column(Text, nullable=False)
    line_start = Column(Integer)
    line_end = Column(Integer)
    cwe_id = Column(String(16))
    severity = Column(String(16))
    confidence = Column(Integer, default=0)
    title = Column(Text)
    description = Column(Text)
    vulnerable_code = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scan = relationship("Scan", back_populates="vulnerabilities")
    patches = relationship("Patch", back_populates="vulnerability", cascade="all, delete-orphan")


class Patch(Base):
    __tablename__ = "patches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vuln_id = Column(String(36), ForeignKey("vulnerabilities.id"), nullable=False)
    diff_content = Column(Text)
    description = Column(Text)
    status = Column(String(16), default=PatchStatus.DRAFT)
    applied_at = Column(DateTime, nullable=True)

    vulnerability = relationship("Vulnerability", back_populates="patches")


# ── Pydantic Schemas ───────────────────────────────────────────────────

class ScanCreate(BaseModel):
    source_type: SourceType
    source_path: str
    language: str | None = None


class ScanResponse(BaseModel):
    id: str
    status: ScanStatus
    source_type: SourceType
    source_path: str
    language: str | None
    total_files: int
    scanned_files: int
    vuln_count_critical: int
    vuln_count_high: int
    vuln_count_medium: int
    vuln_count_low: int
    progress_percent: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VulnerabilityResponse(BaseModel):
    id: str
    scan_id: str
    file_path: str
    line_start: int | None
    line_end: int | None
    cwe_id: str | None
    severity: Severity
    title: str | None
    description: str | None
    vulnerable_code: str | None

    model_config = ConfigDict(from_attributes=True)


class PatchResponse(BaseModel):
    id: str
    vuln_id: str
    diff_content: str | None
    description: str | None
    status: PatchStatus

    model_config = ConfigDict(from_attributes=True)


class ScanProgress(BaseModel):
    type: str = "progress"
    percent: float = 0.0
    current_file: str | None = None


class VulnFound(BaseModel):
    type: str = "vuln_found"
    file: str
    severity: Severity
    title: str


class ScanDone(BaseModel):
    type: str = "scan_done"
    total_vulns: int
    duration: float
