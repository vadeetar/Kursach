"""SQLAlchemy ORM models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class FindingStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    DEFERRED = "deferred"


class AssetStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DECOMMISSIONED = "decommissioned"
    TESTING = "testing"


class Ecosystem(str, Enum):
    PYPI = "pypi"
    NPM = "npm"
    MAVEN = "maven"
    CARGO = "cargo"
    RUBYGEMS = "rubygems"
    NUGET = "nuget"
    COMPOSER = "composer"
    GOLANG = "golang"
    GENERIC = "generic"


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    __table_args__ = (
        UniqueConstraint("cve_id", name="uq_cve_id"),
        Index("idx_cvss_score", "cvss_score"),
        Index("idx_epss_score", "epss_score"),
        Index("idx_severity", "severity"),
    )

    id = Column(Integer, primary_key=True)
    cve_id = Column(String(20), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    summary = Column(String(500))

    cvss_score = Column(Float, nullable=False, default=0.0)
    cvss_vector = Column(String(120))
    severity = Column(SQLEnum(SeverityLevel, native_enum=False), nullable=False)

    epss_score = Column(Float)
    epss_percentile = Column(Float)
    epss_last_updated = Column(DateTime)

    published_date = Column(DateTime, nullable=False)
    last_modified_date = Column(DateTime, nullable=False)

    nvd_url = Column(String(200))
    cwe_ids = Column(JSON)
    has_public_exploit = Column(Boolean, default=False)
    exploitdb_url = Column(String(200))
    affected_products = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    findings = relationship("Finding", back_populates="vulnerability", cascade="all, delete-orphan")

    def get_priority(self) -> str:
        if self.cvss_score >= 8.0 and self.epss_score and self.epss_score > 0.3:
            return "critical"
        if self.cvss_score >= 7.0:
            return "high"
        if self.cvss_score >= 4.0:
            return "medium"
        return "low"


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("ecosystem", "package_name", "version", name="uq_asset_unique"),
        Index("idx_package_name", "package_name"),
        Index("idx_ecosystem", "ecosystem"),
    )

    id = Column(Integer, primary_key=True)
    ecosystem = Column(SQLEnum(Ecosystem, native_enum=False), nullable=False)
    package_name = Column(String(256), nullable=False)
    version = Column(String(50), nullable=False)

    description = Column(Text)
    homepage_url = Column(String(200))
    repository_url = Column(String(200))
    license = Column(String(100))

    status = Column(SQLEnum(AssetStatus, native_enum=False), default=AssetStatus.ACTIVE)
    installed_in = Column(JSON)
    business_criticality = Column(String(20), default="standard")
    owner_team = Column(String(100))

    latest_version = Column(String(50))
    latest_version_date = Column(DateTime)
    can_be_updated = Column(Boolean, default=True)
    update_notes = Column(Text)

    added_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime)

    findings = relationship("Finding", back_populates="asset", cascade="all, delete-orphan")

    def full_identifier(self) -> str:
        return f"{self.ecosystem.value}:{self.package_name}@{self.version}"


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("vulnerability_id", "asset_id", name="uq_finding_unique"),
        Index("idx_finding_status", "status"),
        Index("idx_finding_priority", "priority"),
    )

    id = Column(Integer, primary_key=True)
    vulnerability_id = Column(Integer, ForeignKey("vulnerabilities.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    status = Column(SQLEnum(FindingStatus, native_enum=False), default=FindingStatus.NEW)
    priority = Column(String(20), nullable=False)
    risk_score = Column(Float)

    assigned_to = Column(String(100))
    remediation_due_date = Column(DateTime)
    remediation_notes = Column(Text)

    evidence_notes = Column(Text)
    false_positive = Column(Boolean, default=False)
    false_positive_reason = Column(String(200))

    vulnerable_version = Column(String(50))
    fixed_version = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)

    vulnerability = relationship("Vulnerability", back_populates="findings")
    asset = relationship("Asset", back_populates="findings")

    def days_until_due(self) -> int | None:
        if not self.remediation_due_date:
            return None
        delta = self.remediation_due_date - datetime.utcnow()
        return max(0, delta.days)


class Remediation(Base):
    __tablename__ = "remediations"
    __table_args__ = (
        UniqueConstraint("cve_id", "ecosystem", "package_name", name="uq_remediation_unique"),
    )

    id = Column(Integer, primary_key=True)
    cve_id = Column(String(20), nullable=False, index=True)
    ecosystem = Column(SQLEnum(Ecosystem, native_enum=False), nullable=False)
    package_name = Column(String(256), nullable=False)

    recommended_version = Column(String(50))
    patch_type = Column(String(50))
    release_date = Column(DateTime)

    has_workaround = Column(Boolean, default=False)
    workaround_description = Column(Text)
    notes = Column(Text)
    vendor_advisory_url = Column(String(200))
    source = Column(String(100), default="nvd")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScanMetadata(Base):
    __tablename__ = "scan_metadata"

    id = Column(Integer, primary_key=True)
    scan_type = Column(String(50), nullable=False)
    source = Column(String(100))
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20), default="running")
    records_processed = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    errors = Column(JSON)
    notes = Column(Text)
