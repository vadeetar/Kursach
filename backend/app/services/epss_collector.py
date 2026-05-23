"""EPSS (Exploit Prediction Scoring System) API client."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
from sqlalchemy.orm import Session

from app.models import Vulnerability

logger = logging.getLogger(__name__)


class EPSSCollector:
    BASE_URL = "https://api.first.org/data/v1/epss"

    async def fetch_scores(self, cve_ids: list[str], batch_size: int = 50) -> dict[str, dict[str, Any]]:
        scores: dict[str, dict[str, Any]] = {}
        if not cve_ids:
            return scores

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(cve_ids), batch_size):
                batch = cve_ids[i : i + batch_size]
                try:
                    async with session.get(
                        self.BASE_URL,
                        params={"cve": ",".join(batch)},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            logger.warning("EPSS API status %s", resp.status)
                            continue
                        data = await resp.json()
                        for record in data.get("data", []):
                            cve = record.get("cve")
                            if cve:
                                scores[cve] = {
                                    "score": float(record.get("epss", 0.0)),
                                    "percentile": float(record.get("percentile", 0.0)) * 100,
                                    "timestamp": record.get("date"),
                                }
                except Exception as exc:
                    logger.error("EPSS fetch error: %s", exc)
                await asyncio.sleep(0.3)
        return scores

    def update_database(self, scores: dict[str, dict[str, Any]], db: Session) -> int:
        updated = 0
        for cve_id, data in scores.items():
            vuln = db.query(Vulnerability).filter(Vulnerability.cve_id == cve_id).first()
            if vuln:
                vuln.epss_score = data["score"]
                vuln.epss_percentile = data["percentile"]
                if data.get("timestamp"):
                    try:
                        vuln.epss_last_updated = datetime.fromisoformat(str(data["timestamp"]))
                    except ValueError:
                        vuln.epss_last_updated = datetime.utcnow()
                updated += 1
        db.commit()
        return updated

    def run_update(self, db: Session, limit: int = 100) -> int:
        cve_ids = [v.cve_id for v in db.query(Vulnerability).limit(limit).all()]
        if not cve_ids:
            return 0
        scores = asyncio.run(self.fetch_scores(cve_ids))
        return self.update_database(scores, db)
