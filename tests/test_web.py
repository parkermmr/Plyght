"""
The plyght.web spine: probes, self-hosted docs, security headers,
identity only from a verified proxy, group guards, and the client
address read from the right of X-Forwarded-For.
"""

import pytest

pytest.importorskip("fastapi")

from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from plyght.web import WebSettings, create_app, require_groups
from plyght.web.middleware.proxied_client import forwarded


def client(**settings) -> TestClient:
    app = create_app(WebSettings(name="demo", **settings))
    router = APIRouter()

    @router.get("/whoami")
    def whoami(identity=Depends(require_groups("admins"))) -> dict:
        return {"user": identity.user}

    app.include_router(router, prefix=app.state.settings.api_prefix)
    return TestClient(app)


def test_probes():
    web = client()
    assert web.get("/health").json() == {"status": "ok"}
    assert web.get("/ready").json() == {"status": "ready", "service": "demo"}


def test_ready_reports_degraded_dependencies():
    web = client()

    async def check():
        return {"database": True, "cache": False}

    web.app.state.ready_check = check
    body = web.get("/ready").json()
    assert body["status"] == "degraded"
    assert body["dependencies"] == {"database": True, "cache": False}


def test_docs_are_self_hosted():
    web = client()
    page = web.get("/docs").text
    assert "<script>" not in page
    assert 'src="/static/plyght/swagger-init.js"' in page
    assert web.get("/static/plyght/swagger-init.js").status_code == 200
    assert "googleapis" not in web.get("/redoc").text


def test_security_headers_and_csp_exemption():
    web = client(csp="default-src 'self'", csp_exempt="/static", hsts=True)
    headers = web.get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["content-security-policy"] == "default-src 'self'"
    assert "strict-transport-security" in headers
    exempt = web.get("/static/plyght/swagger-init.js").headers
    assert "content-security-policy" not in exempt


def test_auth_disabled_passes_open():
    assert client().get("/api/v1/whoami").json() == {"user": None}


def test_identity_needs_the_proxy_secret():
    web = client(auth_enabled=True, auth_proxy_secret="s3cret")
    admin = {"x-auth-request-user": "sam", "x-auth-request-groups": "admins, ops"}
    assert web.get("/api/v1/whoami", headers=admin).status_code == 401
    proven = {**admin, "x-auth-proxy-secret": "s3cret"}
    assert web.get("/api/v1/whoami", headers=proven).json() == {"user": "sam"}
    outsider = {**proven, "x-auth-request-groups": "ops"}
    assert web.get("/api/v1/whoami", headers=outsider).status_code == 403


def test_cors_wildcard_never_allows_credentials():
    web = client(cors_origins="*")
    response = web.get("/health", headers={"origin": "https://elsewhere.example"})
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers


def test_forwarded_reads_from_the_right():
    assert forwarded("spoofed, 10.0.0.9", 1) == "10.0.0.9"
    assert forwarded("spoofed, 10.0.0.9, 172.16.0.2", 2) == "10.0.0.9"
    assert forwarded("10.0.0.9", 3) == "10.0.0.9"
    assert forwarded("", 1) is None and forwarded(None, 1) is None
