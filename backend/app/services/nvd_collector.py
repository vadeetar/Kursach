"""NIST NVD API 2.0 client — CVE ingestion."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ScanMetadata, SeverityLevel, Vulnerability

logger = logging.getLogger(__name__)
settings = get_settings()

SEVERITY_MAP = {
    "CRITICAL": SeverityLevel.CRITICAL,
    "HIGH": SeverityLevel.HIGH,
    "MEDIUM": SeverityLevel.MEDIUM,
    "LOW": SeverityLevel.LOW,
    "NONE": SeverityLevel.NONE,
}


@dataclass
class NVDCVERecord:
    cve_id: str
    description: str
    cvss_score: float
    cvss_vector: str
    severity: SeverityLevel
    published_date: datetime
    last_modified_date: datetime
    cwe_ids: list[int]
    affected_products: list[dict[str, Any]]
    nvd_url: str


class NVDCollector:
    """Fetches CVE data from https://services.nvd.nist.gov/rest/json/cves/2.0"""

    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.NVD_API_KEY
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> NVDCollector:
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._session:
            await self._session.close()

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "VulnMgmtPlatform/1.0 (course-project)"}
        if self.api_key:
            headers["apiKey"] = self.api_key
        return headers

    async def fetch_recent_cves(
        self,
        days: int | None = None,
        max_results: int | None = None,
    ) -> list[NVDCVERecord]:
        days = days or settings.NVD_SYNC_DAYS
        max_results = max_results or settings.NVD_MAX_RESULTS

        start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000")
        end = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59.999")

        records: list[NVDCVERecord] = []
        start_index = 0
        page_size = min(100, max_results)

        assert self._session is not None

        while len(records) < max_results:
            params = {
                "pubStartDate": start,
                "pubEndDate": end,
                "startIndex": start_index,
                "resultsPerPage": page_size,
            }
            try:
                async with self._session.get(
                    self.BASE_URL,
                    params=params,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error("NVD API %s: %s", resp.status, text[:200])
                        break
                    data = await resp.json()
            except Exception as exc:
                logger.exception("NVD fetch failed: %s", exc)
                break

            for item in data.get("vulnerabilities", []):
                parsed = self._parse_record(item)
                if parsed:
                    records.append(parsed)
                if len(records) >= max_results:
                    break

            total = data.get("totalResults", 0)
            start_index += page_size
            if start_index >= total or not data.get("vulnerabilities"):
                break
            await asyncio.sleep(6 if not self.api_key else 0.6)

        logger.info("Fetched %d CVE records from NVD", len(records))
        return records

    def _parse_record(self, item: dict[str, Any]) -> NVDCVERecord | None:
        try:
            cve = item.get("cve", {})
            cve_id = cve.get("id")
            if not cve_id:
                return None

            description = ""
            for desc in cve.get("descriptions", []):
                if desc.get("lang") == "en":
                    description = desc.get("value", "")[:4000]
                    break
            if not description:
                description = "No description available"

            cvss_score = 0.0
            cvss_vector = ""
            severity_label = "NONE"
            metrics = cve.get("metrics", {})
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                metric_list = metrics.get(key, [])
                if metric_list:
                    cvss_data = metric_list[0].get("cvssData", {})
                    cvss_score = float(cvss_data.get("baseScore", 0.0))
                    cvss_vector = cvss_data.get("vectorString", "")
                    severity_label = cvss_data.get("baseSeverity", "NONE")
                    break

            severity = SEVERITY_MAP.get(severity_label.upper(), SeverityLevel.NONE)

            cwe_ids: list[int] = []
            for weakness in cve.get("weaknesses", []):
                for desc in weakness.get("description", []):
                    val = desc.get("value", "")
                    if val.startswith("CWE-"):
                        try:
                            cwe_ids.append(int(val.replace("CWE-", "")))
                        except ValueError:
                            pass

            affected_products = self._parse_configurations(cve.get("configurations", []))

            def parse_dt(value: str) -> datetime:
                if not value:
                    return datetime.utcnow()
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)

            return NVDCVERecord(
                cve_id=cve_id,
                description=description,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                severity=severity,
                published_date=parse_dt(cve.get("published", "")),
                last_modified_date=parse_dt(cve.get("lastModified", "")),
                cwe_ids=cwe_ids,
                affected_products=affected_products,
                nvd_url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            )
        except Exception as exc:
            logger.warning("Parse error: %s", exc)
            return None

    def _parse_configurations(self, configurations: list[dict]) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        for config in configurations:
            for node in config.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    if not match.get("vulnerable", True):
                        continue
                    criteria = match.get("criteria", "")
                    parts = criteria.split(":")
                    if len(parts) >= 5:
                        products.append(
                            {
                                "cpe": criteria,
                                "vendor": parts[3] if parts[3] != "*" else None,
                                "product": parts[4] if parts[4] != "*" else None,
                                "version_start": match.get("versionStartIncluding"),
                                "version_end": match.get("versionEndExcluding"),
                            }
                        )
        return products[:50]

    def sync_to_database(self, cves: list[NVDCVERecord], db: Session) -> tuple[int, int]:
        added = updated = 0
        for record in cves:
            existing = db.query(Vulnerability).filter(Vulnerability.cve_id == record.cve_id).first()
            if existing:
                existing.description = record.description
                existing.cvss_score = record.cvss_score
                existing.cvss_vector = record.cvss_vector
                existing.severity = record.severity
                existing.cwe_ids = record.cwe_ids
                existing.affected_products = record.affected_products
                existing.last_modified_date = record.last_modified_date
                existing.nvd_url = record.nvd_url
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                db.add(
                    Vulnerability(
                        cve_id=record.cve_id,
                        description=record.description,
                        summary=record.description[:200],
                        cvss_score=record.cvss_score,
                        cvss_vector=record.cvss_vector,
                        severity=record.severity,
                        published_date=record.published_date,
                        last_modified_date=record.last_modified_date,
                        cwe_ids=record.cwe_ids,
                        affected_products=record.affected_products,
                        nvd_url=record.nvd_url,
                    )
                )
                added += 1
        db.commit()
        return added, updated

    def run_sync(self, db: Session, days: int | None = None) -> tuple[int, int, ScanMetadata]:
        scan = ScanMetadata(
            scan_type="nvd_sync",
            source="nvd.nist.gov",
            started_at=datetime.utcnow(),
            status="running",
        )
        db.add(scan)
        db.commit()

        async def _fetch() -> list[NVDCVERecord]:
            async with NVDCollector(self.api_key) as collector:
                return await collector.fetch_recent_cves(days=days)

        try:
            cves = asyncio.run(_fetch())
            added, updated = self.sync_to_database(cves, db)
            scan.status = "success"
            scan.records_processed = len(cves)
            scan.records_added = added
            scan.records_updated = updated
            scan.completed_at = datetime.utcnow()
            scan.notes = f"Synced {len(cves)} CVEs"
        except Exception as exc:
            scan.status = "failed"
            scan.completed_at = datetime.utcnow()
            scan.errors = [{"message": str(exc)}]
            scan.notes = "Sync failed"
            added, updated = 0, 0
            logger.exception("NVD sync failed")

        db.commit()
        db.refresh(scan)
        return added, updated, scan
