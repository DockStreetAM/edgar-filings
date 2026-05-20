"""Verify HTTP error responses are mapped to typed exceptions with EDGAR metadata."""

from __future__ import annotations

import httpx
import pytest
import respx

from edgar_filings import (
    BETA_HOST,
    AuthError,
    Client,
    EdgarServerError,
    EdgarValidationError,
)
from tests.fixtures.responses import ERROR_400, ERROR_401, ERROR_500


@respx.mock
def test_400_raises_validation_error(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/fm/0000000000/verify").mock(
        return_value=httpx.Response(400, json=ERROR_400)
    )
    with pytest.raises(EdgarValidationError) as ei:
        test_client.verify_credentials("0000000000")
    assert ei.value.status_code == 400
    assert ei.value.tracking == ERROR_400["tracking"]


@respx.mock
def test_401_raises_auth_error(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(401, json=ERROR_401))
    with pytest.raises(AuthError) as ei:
        test_client.get_status()
    assert ei.value.tracking == ERROR_401["tracking"]


@respx.mock
def test_403_raises_auth_error(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(403, json=ERROR_401))
    with pytest.raises(AuthError):
        test_client.get_status()


@respx.mock
def test_500_raises_server_error(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(500, json=ERROR_500))
    with pytest.raises(EdgarServerError):
        test_client.get_status()


@respx.mock
def test_503_raises_server_error(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(503, json=ERROR_500))
    with pytest.raises(EdgarServerError):
        test_client.get_status()


@respx.mock
def test_error_repr_includes_locator(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(401, json=ERROR_401))
    try:
        test_client.get_status()
    except AuthError as e:
        rendered = str(e)
        assert "tracking=" in rendered
        assert "locator=" in rendered
        assert "http=401" in rendered
