"""Match CVE records against organization software inventory."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Asset, AssetStatus, Finding, FindingStatus, ScanMetadata, Vulnerability
from app.services.prioritizer import apply_sla_due_date, compute_priority, compute_risk_score

logger = logging.getLogger(__name__)


def _version_in_range(version: str, product: dict) -> bool:
    """Simplified version check — compares normalized strings."""
    v = version.strip().lower()
    start = product.get("version_start")
    end = product.get("version_end")
    if start and v < str(start).lower():
        return False
    if end and v >= str(end).lower():
        return False
    return True


def _product_matches_asset(product: dict, asset: Asset) -> bool:
    pname = (product.get("product") or "").lower()
    vendor = (product.get("vendor") or "").lower()
    pkg = asset.package_name.lower()

    if pname and pname in pkg or pkg in pname:
        return _version_in_range(asset.version, product)
    if vendor and vendor in pkg:
        return _version_in_range(asset.version, product)
    return False


def _text_match(vuln: Vulnerability, asset: Asset) -> bool:
    text = vuln.description.lower()
    pkg = asset.package_name.lower()
    return len(pkg) > 2 and pkg in text


class VulnerabilityMatcher:
    @staticmethod
    def match_asset(asset: Asset, db: Session) -> list[Finding]:
        findings: list[Finding] = []
        candidates = db.query(Vulnerability).filter(
            or_(
                Vulnerability.affected_products.isnot(None),
                Vulnerability.description.ilike(f"%{asset.package_name}%"),
            )
        ).limit(500).all()

        for vuln in candidates:
            matched = False
            if vuln.affected_products:
                for product in vuln.affected_products:
                    if _product_matches_asset(product, asset):
                        matched = True
                        break
            if not matched and _text_match(vuln, asset):
                matched = True
            if not matched:
                continue

            existing = (
                db.query(Finding)
                .filter(
                    and_(
                        Finding.vulnerability_id == vuln.id,
                        Finding.asset_id == asset.id,
                    )
                )
                .first()
            )
            if existing:
                continue

            priority = compute_priority(vuln, asset)
            finding = Finding(
                vulnerability_id=vuln.id,
                asset_id=asset.id,
                status=FindingStatus.NEW,
                priority=priority,
                risk_score=compute_risk_score(vuln, asset),
                vulnerable_version=asset.version,
                remediation_due_date=apply_sla_due_date(priority),
                evidence_notes=f"Matched package {asset.full_identifier()}",
            )
            db.add(finding)
            findings.append(finding)

        if findings:
            db.commit()
        return findings

    @staticmethod
    def match_all(db: Session) -> tuple[int, int, ScanMetadata]:
        scan = ScanMetadata(
            scan_type="matcher_run",
            source="internal",
            started_at=datetime.utcnow(),
            status="running",
        )
        db.add(scan)
        db.commit()

        total_findings = 0
        assets = db.query(Asset).filter(Asset.status == AssetStatus.ACTIVE).all()
        try:
            for asset in assets:
                created = VulnerabilityMatcher.match_asset(asset, db)
                total_findings += len(created)
                asset.last_checked = datetime.utcnow()
            db.commit()
            scan.status = "success"
            scan.records_processed = len(assets)
            scan.records_added = total_findings
            scan.notes = f"Created {total_findings} findings for {len(assets)} assets"
        except Exception as exc:
            scan.status = "failed"
            scan.errors = [{"message": str(exc)}]
            logger.exception("Matcher failed")

        scan.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(scan)
        return len(assets), total_findings, scan
