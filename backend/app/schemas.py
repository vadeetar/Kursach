"""Pydantic V2 request/response schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


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


class VulnerabilityCreate(BaseModel):
    cve_id: str = Field(..., pattern=r"^CVE-\d{4}-\d{4,}$")
    description: str = Field(..., min_length=10)
    summary: str | None = None
    cvss_score: float = Field(..., ge=0.0, le=10.0)
    cvss_vector: str | None = None
    severity: SeverityLevel
    epss_score: float | None = Field(None, ge=0.0, le=1.0)
    epss_percentile: float | None = Field(None, ge=0.0, le=100.0)
    published_date: datetime
    last_modified_date: datetime
    nvd_url: str | None = None
    cwe_ids: list[int] | None = None
    has_public_exploit: bool = False
    affected_products: list[dict[str, Any]] | None = None


class VulnerabilityUpdate(BaseModel):
    epss_score: float | None = Field(None, ge=0.0, le=1.0)
    epss_percentile: float | None = Field(None, ge=0.0, le=100.0)
    epss_last_updated: datetime | None = None
    has_public_exploit: bool | None = None
    description: str | None = None


class VulnerabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cve_id: str
    description: str
    summary: str | None
    cvss_score: float
    cvss_vector: str | None
    severity: SeverityLevel
    epss_score: float | None
    epss_percentile: float | None
    epss_last_updated: datetime | None
    published_date: datetime
    last_modified_date: datetime
    nvd_url: str | None
    cwe_ids: list[int] | None
    has_public_exploit: bool
    affected_products: list[dict[str, Any]] | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def priority(self) -> str:
        if self.cvss_score >= 8.0 and self.epss_score and self.epss_score > 0.3:
            return "critical"
        if self.cvss_score >= 7.0:
            return "high"
        if self.cvss_score >= 4.0:
            return "medium"
        return "low"


class AssetCreate(BaseModel):
    ecosystem: Ecosystem
    package_name: str = Field(..., min_length=1, max_length=256)
    version: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    status: AssetStatus = AssetStatus.ACTIVE
    installed_in: list[str] | None = None
    business_criticality: str = "standard"
    owner_team: str | None = None


class AssetUpdate(BaseModel):
    status: AssetStatus | None = None
    installed_in: list[str] | None = None
    business_criticality: str | None = None
    owner_team: str | None = None
    update_notes: str | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ecosystem: Ecosystem
    package_name: str
    version: str
    description: str | None
    status: AssetStatus
    installed_in: list[str] | None
    business_criticality: str | None
    owner_team: str | None
    latest_version: str | None
    can_be_updated: bool
    added_at: datetime
    last_checked: datetime | None


class FindingUpdate(BaseModel):
    status: FindingStatus | None = None
    priority: str | None = None
    assigned_to: str | None = None
    remediation_due_date: datetime | None = None
    remediation_notes: str | None = None
    false_positive: bool | None = None
    false_positive_reason: str | None = None


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vulnerability_id: int
    asset_id: int
    status: FindingStatus
    priority: str
    risk_score: float | None
    assigned_to: str | None
    remediation_due_date: datetime | None
    remediation_notes: str | None
    vulnerable_version: str | None
    fixed_version: str | None
    false_positive: bool
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class FindingWithDetails(FindingResponse):
    vulnerability: VulnerabilityResponse
    asset: AssetResponse


class RemediationCreate(BaseModel):
    cve_id: str
    ecosystem: Ecosystem
    package_name: str
    recommended_version: str | None = None
    patch_type: str | None = None
    notes: str | None = None
    source: str = "manual"


class RemediationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cve_id: str
    ecosystem: Ecosystem
    package_name: str
    recommended_version: str | None
    patch_type: str | None
    notes: str | None
    source: str | None
    created_at: datetime


class RiskStats(BaseModel):
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_assets: int
    at_risk_assets: int
    total_findings: int
    findings_new: int
    findings_in_progress: int
    findings_overdue: int
    avg_time_to_fix_days: float | None = None


class ExecutiveSummaryReport(BaseModel):
    generated_at: datetime
    report_period_days: int
    stats: RiskStats
    top_vulnerabilities: list[VulnerabilityResponse]
    most_affected_assets: list[dict[str, Any]]
    recommendations: list[str]


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    services: dict[str, str]
    version: str


class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[Any]


class SyncResult(BaseModel):
    scan_id: int
    added: int
    updated: int
    message: str


class MatchResult(BaseModel):
    assets_processed: int
    findings_created: int
    message: str
