from __future__ import annotations

import httpx
import pytest
import respx

from edgar_filings import BETA_HOST, AsyncClient, Client
from tests.fixtures.responses import STATUS_OK


@respx.mock
def test_get_status_sync(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(200, json=STATUS_OK))
    resp = test_client.get_status()
    assert resp.tracking == STATUS_OK["tracking"]
    assert resp.condition == "ACCEPTING"
    assert resp.message is not None


@respx.mock
def test_get_status_sends_filer_token_no_user(test_client: Client) -> None:
    route = respx.get(f"{BETA_HOST}/status").mock(
        return_value=httpx.Response(200, json=STATUS_OK)
    )
    test_client.get_status()
    request = route.calls.last.request
    # /status takes only the filer token — no comma + user token.
    assert request.headers["authorization"] == "Bearer filer-jwt"
    assert "," not in request.headers["authorization"]
    assert "x-user-token" not in request.headers
    assert "x-edgar-user-token" not in request.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_status_async(async_test_client: AsyncClient) -> None:
    respx.get(f"{BETA_HOST}/status").mock(return_value=httpx.Response(200, json=STATUS_OK))
    resp = await async_test_client.get_status()
    assert resp.condition == "ACCEPTING"
    await async_test_client.aclose()
