"""Tests for app startup, seed data, and root routes."""

import os

from app.database import SessionLocal, engine
from app.models import Asset, Base, Ecosystem, Finding, Vulnerability
from app.seed import seed_demo_data


def test_root_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_web_ui_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_seed_populates_demo_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.environ.pop("DISABLE_SEED", None)

    seed_demo_data()

    db = SessionLocal()
    try:
        assert db.query(Vulnerability).count() >= 3
        assert db.query(Asset).count() >= 3
        assert db.query(Finding).count() >= 3
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_update_asset_endpoint(client, db_session):
    asset = Asset(ecosystem=Ecosystem.PYPI, package_name="flask", version="3.0.0")
    db_session.add(asset)
    db_session.commit()

    r = client.put(
        f"/api/v1/assets/{asset.id}",
        json={"business_criticality": "critical", "owner_team": "security"},
    )
    assert r.status_code == 200
    assert r.json()["business_criticality"] == "critical"
    assert r.json()["owner_team"] == "security"
