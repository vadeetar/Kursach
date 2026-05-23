"""Risk prioritization and SLA calculation."""

from datetime import datetime, timedelta

from app.config import get_settings
from app.models import Asset, Vulnerability

settings = get_settings()


def compute_priority(vuln: Vulnerability, asset: Asset) -> str:
    score = vuln.cvss_score
    if vuln.has_public_exploit and vuln.epss_score:
        score += vuln.epss_score * 2.0
    if asset.business_criticality == "critical":
        score += 1.0
    elif asset.business_criticality == "important":
        score += 0.5

    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


def compute_risk_score(vuln: Vulnerability, asset: Asset) -> float:
    score = vuln.cvss_score * 10.0
    if vuln.epss_score:
        score *= 1.0 + vuln.epss_score
    multipliers = {"critical": 1.5, "important": 1.3, "standard": 1.0, "low": 0.8}
    score *= multipliers.get(asset.business_criticality or "standard", 1.0)
    if vuln.has_public_exploit:
        score *= 1.2
    return min(round(score, 2), 100.0)


def apply_sla_due_date(priority: str) -> datetime:
    days = settings.SLA_DAYS.get(priority, 30)
    return datetime.utcnow() + timedelta(days=days)
