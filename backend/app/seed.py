"""Demo seed data when database is empty."""

import logging
import os
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import (
    Asset,
    AssetStatus,
    Ecosystem,
    Finding,
    FindingStatus,
    SeverityLevel,
    Vulnerability,
)
from app.services.prioritizer import apply_sla_due_date, compute_priority, compute_risk_score

logger = logging.getLogger(__name__)


def seed_demo_data() -> None:
    if os.getenv("DISABLE_SEED") == "1":
        return
    db = SessionLocal()
    try:
        if db.query(Vulnerability).count() > 0:
            return

        logger.info("Seeding demo vulnerability management data...")

        vuln_specs = [
            {
                "cve_id": "CVE-2024-0001",
                "description": "Critical RCE in requests when parsing untrusted headers.",
                "cvss_score": 9.8,
                "severity": SeverityLevel.CRITICAL,
                "epss_score": 0.85,
                "package": "requests",
            },
            {
                "cve_id": "CVE-2024-0002",
                "description": "SQL injection in django ORM when using raw queries.",
                "cvss_score": 7.5,
                "severity": SeverityLevel.HIGH,
                "epss_score": 0.12,
                "package": "django",
            },
            {
                "cve_id": "CVE-2024-0003",
                "description": "Denial of service in lodash merge with large payloads.",
                "cvss_score": 5.3,
                "severity": SeverityLevel.MEDIUM,
                "package": "lodash",
            },
        ]

        now = datetime.utcnow()
        vulns = []
        for spec in vuln_specs:
            v = Vulnerability(
                cve_id=spec["cve_id"],
                description=spec["description"],
                summary=spec["description"][:120],
                cvss_score=spec["cvss_score"],
                severity=spec["severity"],
                epss_score=spec.get("epss_score"),
                published_date=now - timedelta(days=30),
                last_modified_date=now,
                nvd_url=f"https://nvd.nist.gov/vuln/detail/{spec['cve_id']}",
                affected_products=[{"product": spec["package"], "vendor": spec["package"]}],
            )
            vulns.append(v)
            db.add(v)

        assets = [
            Asset(
                ecosystem=Ecosystem.PYPI,
                package_name="requests",
                version="2.28.1",
                business_criticality="critical",
                owner_team="platform",
                installed_in=["api-gateway"],
                status=AssetStatus.ACTIVE,
            ),
            Asset(
                ecosystem=Ecosystem.PYPI,
                package_name="django",
                version="4.2.0",
                business_criticality="important",
                owner_team="web",
                status=AssetStatus.ACTIVE,
            ),
            Asset(
                ecosystem=Ecosystem.NPM,
                package_name="lodash",
                version="4.17.20",
                business_criticality="standard",
                owner_team="frontend",
                status=AssetStatus.ACTIVE,
            ),
        ]
        db.add_all(assets)
        db.commit()

        pkg_to_vuln = {spec["package"]: v for spec, v in zip(vuln_specs, vulns)}
        for asset in assets:
            vuln = pkg_to_vuln.get(asset.package_name)
            if not vuln:
                continue
            priority = compute_priority(vuln, asset)
            db.add(
                Finding(
                    vulnerability_id=vuln.id,
                    asset_id=asset.id,
                    status=FindingStatus.NEW,
                    priority=priority,
                    risk_score=compute_risk_score(vuln, asset),
                    vulnerable_version=asset.version,
                    remediation_due_date=apply_sla_due_date(priority),
                    assigned_to=asset.owner_team,
                )
            )
        db.commit()
        logger.info("Demo seed completed")
    finally:
        db.close()
