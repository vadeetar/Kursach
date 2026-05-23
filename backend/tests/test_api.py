"""Integration tests for REST API."""

from datetime import datetime

from app.models import Asset, Ecosystem, Finding, FindingStatus, SeverityLevel, Vulnerability


def _seed_finding(db_session):
    vuln = Vulnerability(
        cve_id="CVE-2023-TEST-1",
        description="Test vulnerability description for API tests",
        cvss_score=8.0,
        severity=SeverityLevel.HIGH,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )
    asset = Asset(
        ecosystem=Ecosystem.PYPI,
        package_name="testpkg",
        version="1.0.0",
        business_criticality="standard",
    )
    db_session.add_all([vuln, asset])
    db_session.commit()
    finding = Finding(
        vulnerability_id=vuln.id,
        asset_id=asset.id,
        status=FindingStatus.NEW,
        priority="high",
        risk_score=75.0,
    )
    db_session.add(finding)
    db_session.commit()
    return finding, vuln, asset


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("healthy", "degraded")


def test_create_and_list_assets(client):
    r = client.post(
        "/api/v1/assets",
        json={
            "ecosystem": "pypi",
            "package_name": "flask",
            "version": "2.0.0",
            "business_criticality": "important",
        },
    )
    assert r.status_code == 201
    r2 = client.get("/api/v1/assets")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1


def test_list_findings_and_update(client, db_session):
    finding, _, _ = _seed_finding(db_session)
    r = client.get("/api/v1/findings?priority=high")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r2 = client.patch(
        f"/api/v1/findings/{finding.id}",
        json={"status": "in_progress", "assigned_to": "security-team"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "in_progress"


def test_risk_stats(client, db_session):
    _seed_finding(db_session)
    r = client.get("/api/v1/stats/risk")
    assert r.status_code == 200
    data = r.json()
    assert data["total_findings"] >= 1


def test_executive_summary(client, db_session):
    _seed_finding(db_session)
    r = client.get("/api/v1/reports/executive-summary")
    assert r.status_code == 200
    assert "recommendations" in r.json()
