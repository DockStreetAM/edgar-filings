from __future__ import annotations

import httpx
import pytest
import respx

from edgar_filings import BETA_HOST, AsyncClient, AuthError, Client
from tests.fixtures.responses import FILER_CHECK_OK, FILER_INFO_OK


@respx.mock
def test_view_filer(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/fm/0000000000").mock(
        return_value=httpx.Response(200, json=FILER_INFO_OK)
    )
    resp = test_client.view_filer("0000000000")
    assert resp.filer_info[0].cik == "0000000000"
    assert resp.filer_info[0].company_conformed_name == "Example Co"


@respx.mock
def test_verify_credentials_sends_both_tokens(test_client: Client) -> None:
    route = respx.get(f"{BETA_HOST}/fm/0000000000/verify").mock(
        return_value=httpx.Response(200, json=FILER_CHECK_OK)
    )
    test_client.verify_credentials("0000000000")
    req = route.calls.last.request
    # Both tokens ride in the single Authorization header, comma-separated.
    # Filer first, user second — the SEC EDGAR API Development Toolkit
    # convention from api-bravo.edgarfiling.sec.gov/resources.
    assert req.headers["authorization"] == "Bearer filer-jwt,user-jwt"
    assert "x-user-token" not in req.headers


@respx.mock
def test_verify_credentials_returns_can_file(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/fm/0000000000/verify").mock(
        return_value=httpx.Response(200, json=FILER_CHECK_OK)
    )
    resp = test_client.verify_credentials("0000000000")
    assert resp.can_file is True


@respx.mock
def test_set_custom_ccc_sends_both_current_and_new(test_client: Client) -> None:
    route = respx.put(f"{BETA_HOST}/fm/0000000000/ccc").mock(
        return_value=httpx.Response(
            200,
            json={
                "tracking": "t",
                "locator": "l",
                "messages": [],
                "ccc": "$newpass!",
            },
        )
    )
    resp = test_client.set_custom_ccc("0000000000", "$current!", "$newpass!")
    assert resp.ccc == "$newpass!"
    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/json")
    # Both ccc and newCCC must be on the wire per the OpenAPI UpdateCCC schema.
    assert b'"ccc":"$current!"' in req.content
    assert b'"newCCC":"$newpass!"' in req.content


def test_view_filer_without_user_token_raises() -> None:
    with Client("filer-jwt", user_token=None, mode="test") as client:
        with pytest.raises(AuthError):
            client.view_filer("0000000000")


@pytest.mark.asyncio
@respx.mock
async def test_view_filer_async(async_test_client: AsyncClient) -> None:
    respx.get(f"{BETA_HOST}/fm/0000000000").mock(
        return_value=httpx.Response(200, json=FILER_INFO_OK)
    )
    resp = await async_test_client.view_filer("0000000000")
    assert resp.filer_info[0].cik == "0000000000"
    await async_test_client.aclose()
