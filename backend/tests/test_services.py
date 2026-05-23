"""Tests for NVD parsing and prioritization."""

from datetime import datetime

import pytest

from app.models import Asset, Ecosystem, SeverityLevel, Vulnerability
from app.services.matcher import _product_matches_asset, _text_match
from app.services.nvd_collector import NVDCollector
from app.services.prioritizer import compute_priority, compute_risk_score


def test_compute_priority_critical_asset():
    vuln = Vulnerability(
        cve_id="CVE-1",
        description="x",
        cvss_score=8.5,
        severity=SeverityLevel.HIGH,
        epss_score=0.5,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )
    asset = Asset(
        ecosystem=Ecosystem.PYPI,
        package_name="pkg",
        version="1.0",
        business_criticality="critical",
    )
    assert compute_priority(vuln, asset) == "critical"


def test_compute_risk_score_capped():
    vuln = Vulnerability(
        cve_id="CVE-2",
        description="x",
        cvss_score=10.0,
        severity=SeverityLevel.CRITICAL,
        epss_score=0.99,
        has_public_exploit=True,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )
    asset = Asset(
        ecosystem=Ecosystem.PYPI,
        package_name="pkg",
        version="1.0",
        business_criticality="critical",
    )
    assert compute_risk_score(vuln, asset) == 100.0


def test_nvd_parse_record():
    collector = NVDCollector()
    sample = {
        "cve": {
            "id": "CVE-2024-1234",
            "descriptions": [{"lang": "en", "value": "Sample vulnerability"}],
            "published": "2024-01-15T10:00:00.000",
            "lastModified": "2024-01-16T10:00:00.000",
            "metrics": {
                "cvssMetricV31": [
                    {
                        "cvssData": {
                            "version": "3.1",
                            "baseScore": 7.5,
                            "baseSeverity": "HIGH",
                            "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
                        }
                    }
                ]
            },
            "weaknesses": [
                {"description": [{"lang": "en", "value": "CWE-79"}]}
            ],
            "configurations": [],
        }
    }
    record = collector._parse_record(sample)
    assert record is not None
    assert record.cve_id == "CVE-2024-1234"
    assert record.cvss_score == 7.5
    assert record.severity == SeverityLevel.HIGH


def test_product_matches_asset():
    asset = Asset(ecosystem=Ecosystem.PYPI, package_name="requests", version="2.28.0")
    product = {"product": "requests", "version_end": "2.31.0"}
    assert _product_matches_asset(product, asset) is True


def test_text_match():
    vuln = Vulnerability(
        cve_id="CVE-X",
        description="Buffer overflow in openssl library",
        cvss_score=5.0,
        severity=SeverityLevel.MEDIUM,
        published_date=datetime.utcnow(),
        last_modified_date=datetime.utcnow(),
    )
    asset = Asset(ecosystem=Ecosystem.GENERIC, package_name="openssl", version="1.1.1")
    assert _text_match(vuln, asset) is True
