"""Defensive tests around the LIVE/TEST mode safety rails."""

from __future__ import annotations

import httpx
import pytest
import respx

from edgar_filings import BETA_HOST, PROD_HOST, Client, LiveModeNotConfirmed, stamp_live_test_flag
from tests.fixtures.responses import SUBMISSION_ACCEPTED


def _xml(flag: str) -> bytes:
    return (
        f'<?xml version="1.0" ?>'
        f'<cor:edgarSubmission xmlns:cor="http://www.sec.gov/edgar/coreg">'
        f"<cor:liveTestFlag>{flag}</cor:liveTestFlag>"
        f"</cor:edgarSubmission>"
    ).encode()


def test_stamp_test_overrides_live() -> None:
    stamped = stamp_live_test_flag(_xml("LIVE"), "test")
    assert b"<cor:liveTestFlag>TEST</cor:liveTestFlag>" in stamped


def test_stamp_live_overrides_test() -> None:
    stamped = stamp_live_test_flag(_xml("TEST"), "live")
    assert b"<cor:liveTestFlag>LIVE</cor:liveTestFlag>" in stamped


def test_stamp_rejects_invalid_xml() -> None:
    with pytest.raises(ValueError):
        stamp_live_test_flag(b"not xml", "test")


def test_stamp_rejects_missing_flag() -> None:
    with pytest.raises(ValueError):
        stamp_live_test_flag(
            b'<?xml version="1.0"?><cor:edgarSubmission xmlns:cor="x"/>', "test"
        )


@respx.mock
def test_test_mode_never_hits_prod_host() -> None:
    with Client("filer-jwt", "user-jwt", mode="test") as client:
        # Mount catch-all on PROD_HOST to fail loudly if ever hit
        prod_route = respx.post(f"{PROD_HOST}/submission/single/live").mock(
            return_value=httpx.Response(500)
        )
        beta_route = respx.post(f"{BETA_HOST}/submission/single/test").mock(
            return_value=httpx.Response(202, json=SUBMISSION_ACCEPTED)
        )
        client.submit(_xml("TEST"))
        assert beta_route.called
        assert not prod_route.called


def test_live_mode_blocks_unconfirmed_submit() -> None:
    with Client("filer-jwt", "user-jwt", mode="live") as client:
        with pytest.raises(LiveModeNotConfirmed):
            client.submit(_xml("LIVE"))


def test_live_mode_blocks_unconfirmed_bulk_submit() -> None:
    with Client("filer-jwt", "user-jwt", mode="live") as client:
        with pytest.raises(LiveModeNotConfirmed):
            client.submit_bulk(_xml("LIVE"))


def test_host_override_respected() -> None:
    with Client("filer-jwt", "user-jwt", mode="test", host="https://example.invalid") as client:
        assert client.host == "https://example.invalid"


def test_default_test_uses_beta_host() -> None:
    with Client("filer-jwt", "user-jwt", mode="test") as client:
        assert client.host == BETA_HOST


def test_default_live_uses_prod_host() -> None:
    with Client("filer-jwt", "user-jwt", mode="live") as client:
        assert client.host == PROD_HOST
