"""REST API routes for vulnerability management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Asset,
    AssetStatus,
    Ecosystem,
    Finding,
    FindingStatus,
    Remediation,
    SeverityLevel,
    Vulnerability,
)
from app.schemas import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    ExecutiveSummaryReport,
    FindingResponse,
    FindingStatus as FindingStatusSchema,
    FindingUpdate,
    FindingWithDetails,
    HealthCheckResponse,
    MatchResult,
    PaginatedResponse,
    RemediationCreate,
    RemediationResponse,
    RiskStats,
    SyncResult,
    VulnerabilityCreate,
    VulnerabilityResponse,
    VulnerabilityUpdate,
)
from app.services.epss_collector import EPSSCollector
from app.services.matcher import VulnerabilityMatcher
from app.services.nvd_collector import NVDCollector

settings = get_settings()
router = APIRouter(prefix=settings.API_PREFIX)


@router.get("/health", response_model=HealthCheckResponse)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    return HealthCheckResponse(
        status="healthy" if db_status == "ok" else "degraded",
        timestamp=datetime.utcnow(),
        services={
            "postgres": db_status,
            "data": f"{db.query(Vulnerability).count()} CVEs, {db.query(Asset).count()} assets",
        },
        version=settings.API_VERSION,
    )


@router.post("/vulnerabilities", response_model=VulnerabilityResponse, status_code=201)
def create_vulnerability(vuln: VulnerabilityCreate, db: Session = Depends(get_db)):
    if db.query(Vulnerability).filter(Vulnerability.cve_id == vuln.cve_id).first():
        raise HTTPException(status_code=409, detail=f"CVE {vuln.cve_id} already exists")
    db_vuln = Vulnerability(
        **vuln.model_dump(),
        nvd_url=vuln.nvd_url or f"https://nvd.nist.gov/vuln/detail/{vuln.cve_id}",
    )
    db.add(db_vuln)
    db.commit()
    db.refresh(db_vuln)
    return db_vuln


@router.get("/vulnerabilities")
def list_vulnerabilities(
    min_cvss: float | None = Query(None, ge=0, le=10),
    max_cvss: float | None = Query(None, ge=0, le=10),
    severity: SeverityLevel | None = None,
    has_exploit: bool | None = None,
    min_epss: float | None = Query(None, ge=0, le=1),
    search_text: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Vulnerability)
    if min_cvss is not None:
        query = query.filter(Vulnerability.cvss_score >= min_cvss)
    if max_cvss is not None:
        query = query.filter(Vulnerability.cvss_score <= max_cvss)
    if severity:
        query = query.filter(Vulnerability.severity == severity)
    if has_exploit is not None:
        query = query.filter(Vulnerability.has_public_exploit == has_exploit)
    if min_epss is not None:
        query = query.filter(Vulnerability.epss_score >= min_epss)
    if search_text:
        query = query.filter(
            Vulnerability.description.ilike(f"%{search_text}%")
            | Vulnerability.cve_id.ilike(f"%{search_text}%")
        )
    total = query.count()
    items = query.order_by(desc(Vulnerability.cvss_score)).offset(skip).limit(limit).all()
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items).model_dump()


@router.get("/vulnerabilities/{cve_id}", response_model=VulnerabilityResponse)
def get_vulnerability(cve_id: str, db: Session = Depends(get_db)):
    vuln = db.query(Vulnerability).filter(Vulnerability.cve_id == cve_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="CVE not found")
    return vuln


@router.put("/vulnerabilities/{cve_id}", response_model=VulnerabilityResponse)
def update_vulnerability(cve_id: str, data: VulnerabilityUpdate, db: Session = Depends(get_db)):
    vuln = db.query(Vulnerability).filter(Vulnerability.cve_id == cve_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="CVE not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vuln, field, value)
    vuln.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vuln)
    return vuln


@router.post("/assets", response_model=AssetResponse, status_code=201)
def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Asset)
        .filter(
            Asset.ecosystem == asset.ecosystem,
            Asset.package_name == asset.package_name,
            Asset.version == asset.version,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Asset already exists")
    db_asset = Asset(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    VulnerabilityMatcher.match_asset(db_asset, db)
    return db_asset


@router.get("/assets")
def list_assets(
    ecosystem: Ecosystem | None = None,
    status: AssetStatus | None = None,
    search_text: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Asset)
    if ecosystem:
        query = query.filter(Asset.ecosystem == ecosystem)
    if status:
        query = query.filter(Asset.status == status)
    if search_text:
        query = query.filter(Asset.package_name.ilike(f"%{search_text}%"))
    total = query.count()
    items = query.order_by(Asset.package_name).offset(skip).limit(limit).all()
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items).model_dump()


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: int, data: AssetUpdate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()


@router.get("/findings")
def list_findings(
    status: FindingStatus | None = None,
    priority: str | None = None,
    asset_id: int | None = None,
    overdue_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Finding)
    if status:
        query = query.filter(Finding.status == status)
    if priority:
        query = query.filter(Finding.priority == priority)
    if asset_id:
        query = query.filter(Finding.asset_id == asset_id)
    if overdue_only:
        query = query.filter(
            and_(
                Finding.remediation_due_date < datetime.utcnow(),
                Finding.status != FindingStatus.FIXED,
            )
        )
    total = query.count()
    items = query.order_by(desc(Finding.risk_score), desc(Finding.created_at)).offset(skip).limit(limit).all()
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items).model_dump()


@router.get("/findings/{finding_id}", response_model=FindingWithDetails)
def get_finding(finding_id: int, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
def update_finding(finding_id: int, data: FindingUpdate, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(finding, field, value)
    if data.status == FindingStatusSchema.FIXED:
        finding.resolved_at = datetime.utcnow()
    finding.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(finding)
    return finding


@router.post("/remediations", response_model=RemediationResponse, status_code=201)
def create_remediation(data: RemediationCreate, db: Session = Depends(get_db)):
    rem = Remediation(**data.model_dump())
    db.add(rem)
    db.commit()
    db.refresh(rem)
    return rem


@router.get("/remediations")
def list_remediations(
    cve_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Remediation)
    if cve_id:
        query = query.filter(Remediation.cve_id == cve_id)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items).model_dump()


@router.get("/stats/risk", response_model=RiskStats)
def get_risk_stats(db: Session = Depends(get_db)):
    resolved = (
        db.query(Finding)
        .filter(Finding.status == FindingStatus.FIXED, Finding.resolved_at.isnot(None))
        .all()
    )
    avg_days = None
    if resolved:
        deltas = [(f.resolved_at - f.created_at).days for f in resolved if f.resolved_at and f.created_at]
        if deltas:
            avg_days = round(sum(deltas) / len(deltas), 1)

    at_risk = (
        db.query(func.count(func.distinct(Finding.asset_id)))
        .filter(Finding.status != FindingStatus.FIXED)
        .scalar()
        or 0
    )

    return RiskStats(
        total_vulnerabilities=db.query(Vulnerability).count(),
        critical_count=db.query(Vulnerability).filter(Vulnerability.severity == SeverityLevel.CRITICAL).count(),
        high_count=db.query(Vulnerability).filter(Vulnerability.severity == SeverityLevel.HIGH).count(),
        medium_count=db.query(Vulnerability).filter(Vulnerability.severity == SeverityLevel.MEDIUM).count(),
        low_count=db.query(Vulnerability).filter(Vulnerability.severity == SeverityLevel.LOW).count(),
        total_assets=db.query(Asset).count(),
        at_risk_assets=at_risk,
        total_findings=db.query(Finding).count(),
        findings_new=db.query(Finding).filter(Finding.status == FindingStatus.NEW).count(),
        findings_in_progress=db.query(Finding).filter(Finding.status == FindingStatus.IN_PROGRESS).count(),
        findings_overdue=db.query(Finding)
        .filter(
            Finding.remediation_due_date < datetime.utcnow(),
            Finding.status != FindingStatus.FIXED,
        )
        .count(),
        avg_time_to_fix_days=avg_days,
    )


@router.get("/reports/executive-summary", response_model=ExecutiveSummaryReport)
def executive_summary(db: Session = Depends(get_db)):
    stats = get_risk_stats(db)
    top_vulns = db.query(Vulnerability).order_by(desc(Vulnerability.cvss_score)).limit(5).all()
    affected = (
        db.query(Asset.package_name, func.count(Finding.id).label("cnt"))
        .join(Finding, Finding.asset_id == Asset.id)
        .group_by(Asset.package_name)
        .order_by(desc("cnt"))
        .limit(5)
        .all()
    )
    recommendations = [
        "Обновите пакеты с CVSS ≥ 9.0 в течение 7 дней (SLA critical).",
        f"Просроченных находок: {stats.findings_overdue} — требуется эскалация.",
        "Включите ежедневную синхронизацию NVD и сопоставление с инвентаризацией.",
    ]
    return ExecutiveSummaryReport(
        generated_at=datetime.utcnow(),
        report_period_days=30,
        stats=stats,
        top_vulnerabilities=top_vulns,
        most_affected_assets=[{"package": name, "findings_count": cnt} for name, cnt in affected],
        recommendations=recommendations,
    )


@router.post("/tasks/sync-nvd", response_model=SyncResult)
def sync_nvd(days: int | None = Query(None, ge=1, le=120), db: Session = Depends(get_db)):
    collector = NVDCollector()
    added, updated, scan = collector.run_sync(db, days=days)
    return SyncResult(
        scan_id=scan.id,
        added=added,
        updated=updated,
        message=f"NVD sync: +{added} new, ~{updated} updated ({scan.status})",
    )


@router.post("/tasks/update-epss")
def update_epss(db: Session = Depends(get_db)):
    updated = EPSSCollector().run_update(db)
    return {"updated": updated, "message": f"EPSS scores updated for {updated} CVEs"}


@router.post("/tasks/match-assets", response_model=MatchResult)
def match_assets(db: Session = Depends(get_db)):
    assets_count, findings_count, scan = VulnerabilityMatcher.match_all(db)
    return MatchResult(
        assets_processed=assets_count,
        findings_created=findings_count,
        message=scan.notes or "Matching completed",
    )
