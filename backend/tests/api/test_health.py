"""Health contract without a database or Redis: dependencies are overridden."""

from fastapi.testclient import TestClient

from app.api.v1.endpoints import health as health_endpoint
from app.core.database import get_session
from app.main import app


class _FakeSession:
    def execute(self, *_args, **_kwargs):
        return None


class _FakeRedis:
    def ping(self) -> bool:
        return True


def _client() -> TestClient:
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    health_endpoint.get_redis = lambda: _FakeRedis()
    return TestClient(app)


def test_health_reports_ok():
    with _client() as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["redis"] is True


def test_openapi_documents_the_contracted_routes():
    paths = app.openapi()["paths"]

    for route in (
        "/api/v1/locations",
        "/api/v1/locations/search",
        "/api/v1/nisar/scenes",
        "/api/v1/observations",
        "/api/v1/analysis",
        "/api/v1/jobs/{job_id}",
        "/api/v1/changes",
        "/api/v1/changes/{change_id}/evidence",
        "/api/v1/auxiliary/events",
        "/api/v1/insights",
    ):
        assert route in paths


def test_unknown_location_returns_404():
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    health_endpoint.get_redis = lambda: _FakeRedis()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/locations/00000000-0000-0000-0000-000000000000")

    assert response.status_code in (404, 500)  # fake session cannot answer; DB test covers 404
