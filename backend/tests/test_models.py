"""Unit tests for domain models."""

from datetime import datetime

from app.models import SeverityLevel, Vulnerability


def test_vulnerability_get_priority_critical():
    vuln = Vulnerability(
        cve_id="CVE-2023-12345",
        description="test",
        cvss_score=9.1,
        epss_score=0.95,
        severity=SeverityLevel.CRITICAL,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )
    assert vuln.get_priority() == "critical"


def test_vulnerability_get_priority_high_without_epss():
    vuln = Vulnerability(
        cve_id="CVE-2023-99999",
        description="test",
        cvss_score=8.0,
        epss_score=0.01,
        severity=SeverityLevel.HIGH,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )
    assert vuln.get_priority() == "high"
