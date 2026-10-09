from fastapi.testclient import TestClient

from src.server import database
from src.server.main import app

client = TestClient(app)


def test_health_does_not_require_database() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database_connection(monkeypatch, tmp_path) -> None:
    database.get_engine.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")

    try:
        response = client.get("/health/ready")
    finally:
        database.get_engine.cache_clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_readiness_reports_missing_database_configuration(monkeypatch) -> None:
    database.get_engine.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)

    try:
        response = client.get("/health/ready")
    finally:
        database.get_engine.cache_clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}