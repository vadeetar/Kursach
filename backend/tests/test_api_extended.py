"""Additional API tests for coverage and regression."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models import (
    Asset,
    Ecosystem,
    Finding,
    FindingStatus,
    ScanMetadata,
    SeverityLevel,
    Vulnerability,
)


def _vuln(cve: str = "CVE-2024-TEST-99") -> Vulnerability:
    return Vulnerability(
        cve_id=cve,
        description="Extended API test vulnerability record",
        cvss_score=6.5,
        severity=SeverityLevel.MEDIUM,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )


def test_list_vulnerabilities_with_search(client, db_session):
    db_session.add(_vuln())
    db_session.commit()
    r = client.get("/api/v1/vulnerabilities?search_text=CVE-2024-TEST")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_get_vulnerability_by_cve(client, db_session):
    db_session.add(_vuln("CVE-2024-GET-1"))
    db_session.commit()
    r = client.get("/api/v1/vulnerabilities/CVE-2024-GET-1")
    assert r.status_code == 200
    assert r.json()["cve_id"] == "CVE-2024-GET-1"


def test_create_remediation(client, db_session):
    r = client.post(
        "/api/v1/remediations",
        json={
            "cve_id": "CVE-2024-REM-1",
            "ecosystem": "pypi",
            "package_name": "requests",
            "recommended_version": "2.32.0",
            "patch_type": "security",
        },
    )
    assert r.status_code == 201
    assert r.json()["recommended_version"] == "2.32.0"


def test_delete_asset(client, db_session):
    asset = Asset(ecosystem=Ecosystem.PYPI, package_name="todelete", version="1.0.0")
    db_session.add(asset)
    db_session.commit()
    r = client.delete(f"/api/v1/assets/{asset.id}")
    assert r.status_code == 204


def test_overdue_findings_filter(client, db_session):
    from datetime import timedelta

    vuln = _vuln("CVE-2024-OVER-1")
    asset = Asset(ecosystem=Ecosystem.PYPI, package_name="pkg", version="1.0")
    db_session.add_all([vuln, asset])
    db_session.commit()
    finding = Finding(
        vulnerability_id=vuln.id,
        asset_id=asset.id,
        status=FindingStatus.NEW,
        priority="high",
        remediation_due_date=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(finding)
    db_session.commit()
    r = client.get("/api/v1/findings?overdue_only=true")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@patch("app.api.routes.NVDCollector")
def test_sync_nvd_endpoint(mock_collector_cls, client):
    scan = ScanMetadata(scan_type="nvd_sync", source="test", started_at=datetime.utcnow())
    scan.id = 1
    instance = MagicMock()
    instance.run_sync.return_value = (2, 1, scan)
    mock_collector_cls.return_value = instance

    r = client.post("/api/v1/tasks/sync-nvd")
    assert r.status_code == 200
    body = r.json()
    assert body["added"] == 2
    assert "NVD sync" in body["message"]


@patch("app.api.routes.EPSSCollector")
def test_update_epss_endpoint(mock_collector_cls, client):
    instance = MagicMock()
    instance.run_update.return_value = 5
    mock_collector_cls.return_value = instance

    r = client.post("/api/v1/tasks/update-epss")
    assert r.status_code == 200
    assert r.json()["updated"] == 5


@patch("app.api.routes.VulnerabilityMatcher")
def test_match_assets_endpoint(mock_matcher, client):
    scan = ScanMetadata(scan_type="matcher_run", source="test", started_at=datetime.utcnow())
    scan.id = 2
    scan.notes = "ok"
    mock_matcher.match_all.return_value = (3, 2, scan)

    r = client.post("/api/v1/tasks/match-assets")
    assert r.status_code == 200
    assert r.json()["findings_created"] == 2
