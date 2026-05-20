from __future__ import annotations

import httpx
import pytest
import respx
from lxml import etree

from edgar_filings import BETA_HOST, PROD_HOST, AsyncClient, Client, SubmissionBuilder
from tests.fixtures.responses import SUBMISSION_ACCEPTED, SUBMISSION_STATUS_DONE


def _example_xml(mode_flag: str = "TEST") -> bytes:
    return (
        f'<?xml version="1.0" ?>'
        f'<cor:edgarSubmission xmlns:cor="http://www.sec.gov/edgar/coreg" '
        f'xmlns:com="http://www.sec.gov/edgar/common">'
        f"<cor:liveTestFlag>{mode_flag}</cor:liveTestFlag>"
        f"<cor:submissionType>13F-HR</cor:submissionType>"
        f"</cor:edgarSubmission>"
    ).encode()


@respx.mock
def test_submit_test_goes_to_test_endpoint(test_client: Client) -> None:
    route = respx.post(f"{BETA_HOST}/submission/single/test").mock(
        return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
    )
    resp = test_client.submit(_example_xml("LIVE"))  # wrong flag, should be rewritten
    assert resp.accession_number == "0001234567-26-000001"
    request = route.calls.last.request
    assert b"<cor:liveTestFlag>TEST</cor:liveTestFlag>" in request.content


@respx.mock
def test_submit_live_requires_confirm(live_client: Client) -> None:
    respx.post(f"{PROD_HOST}/submission/single/live").mock(
        return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
    )
    with pytest.raises(Exception) as ei:
        live_client.submit(_example_xml("LIVE"))
    assert "confirm_live" in str(ei.value)


@respx.mock
def test_submit_live_with_confirm(live_client: Client) -> None:
    route = respx.post(f"{PROD_HOST}/submission/single/live").mock(
        return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
    )
    resp = live_client.submit(_example_xml("LIVE"), confirm_live=True)
    assert resp.accession_number == "0001234567-26-000001"
    assert route.called
    assert b"<cor:liveTestFlag>LIVE</cor:liveTestFlag>" in route.calls.last.request.content


@respx.mock
def test_submit_passes_login_cik_header(test_client: Client) -> None:
    route = respx.post(f"{BETA_HOST}/submission/single/test").mock(
        return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
    )
    test_client.submit(_example_xml(), login_cik="0000350001")
    assert route.calls.last.request.headers["x-edgar-login-cik"] == "0000350001"


@respx.mock
def test_submit_bulk(test_client: Client) -> None:
    bulk_response = {
        "tracking": "t",
        "locator": "l",
        "messages": [],
        "submissions": [SUBMISSION_ACCEPTED],
    }
    respx.post(f"{BETA_HOST}/submission/bulk/test").mock(
        return_value=httpx.Response(202, json=bulk_response)
    )
    resp = test_client.submit_bulk(_example_xml())
    assert resp.submissions[0].accession_number == "0001234567-26-000001"


@respx.mock
def test_get_submission_status(test_client: Client) -> None:
    respx.get(f"{BETA_HOST}/submission/0001234567-26-000001/status").mock(
        return_value=httpx.Response(200, json=SUBMISSION_STATUS_DONE)
    )
    resp = test_client.get_submission_status("0001234567-26-000001")
    assert resp.processing_status == "DONE"
    assert resp.final is True


@respx.mock
def test_get_submission_status_no_user_token(test_client: Client) -> None:
    route = respx.get(f"{BETA_HOST}/submission/0001234567-26-000001/status").mock(
        return_value=httpx.Response(200, json=SUBMISSION_STATUS_DONE)
    )
    test_client.get_submission_status("0001234567-26-000001")
    assert "x-user-token" not in route.calls.last.request.headers
    assert "x-edgar-user-token" not in route.calls.last.request.headers


@respx.mock
def test_get_submission_statuses_bulk(test_client: Client) -> None:
    bulk_response = {
        "tracking": "t",
        "locator": "l",
        "messages": [],
        "statuses": [SUBMISSION_STATUS_DONE],
    }
    route = respx.post(f"{BETA_HOST}/submission/status").mock(
        return_value=httpx.Response(200, json=bulk_response)
    )
    resp = test_client.get_submission_statuses(["0001234567-26-000001"])
    assert resp.statuses[0].submission_form_type == "13F-HR"
    sent_body = route.calls.last.request.content
    assert b"accessionNumbers" in sent_body


@respx.mock
def test_submit_builder_round_trip(test_client: Client) -> None:
    xml = (
        SubmissionBuilder(
            form_type="13F-HR",
            filer_cik="0001234567",
            ccc="$secret",
            mode="test",
        )
        .add_flag("confirmingCopyFlag", False)
        .add_field("periodOfReport", "12-31-2025")
        .add_document("primary_doc.xml", "13F-HR", b"<xml/>")
        .build()
    )
    route = respx.post(f"{BETA_HOST}/submission/single/test").mock(
        return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
    )
    test_client.submit(xml)
    sent = route.calls.last.request.content
    # Builder XML was sent with TEST flag intact
    assert b"<cor:liveTestFlag>TEST</cor:liveTestFlag>" in sent
    assert b"13F-HR" in sent
    # Round-trip parse
    parsed = etree.fromstring(sent)
    assert parsed.tag.endswith("edgarSubmission")


@pytest.mark.asyncio
@respx.mock
async def test_submit_async(async_test_client: AsyncClient) -> None:
    respx.post(f"{BETA_HOST}/submission/single/test").mock(
        return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
    )
    resp = await async_test_client.submit(_example_xml())
    assert resp.accession_number == "0001234567-26-000001"
    await async_test_client.aclose()
