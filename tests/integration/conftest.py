"""Integration tests run against api-bravo.edgarfiling.sec.gov (EDGAR Beta).

CI replays VCR cassettes; re-recording requires real beta credentials. Set:

    BETA_FILER_TOKEN
    BETA_USER_TOKEN
    BETA_CIK
    BETA_CCC

Then run::

    uv run pytest tests/integration/ --record-mode=once

The vcr_config below scrubs the Authorization and X-EDGAR-USER-TOKEN headers
before cassettes are written to disk so we never commit real JWTs. The CCC
appears in submission XML bodies; the recorded cassette body should be
post-processed to scrub it before commit (see ``scripts/scrub_cassettes.py``
if it grows beyond manual review).
"""

from __future__ import annotations

import os
import re

import pytest

from edgar_filings import BETA_HOST, Client

# Placeholder values are returned when env vars are unset so cassettes can
# replay in CI without secrets. During recording the env vars must be set
# (`--record-mode=once` will write whatever the placeholders return into the
# cassette, which is not what we want).


@pytest.fixture(scope="session")
def beta_filer_token() -> str:
    return os.environ.get("BETA_FILER_TOKEN") or "placeholder-filer-jwt-for-replay"


@pytest.fixture(scope="session")
def beta_user_token() -> str:
    return os.environ.get("BETA_USER_TOKEN") or "placeholder-user-jwt-for-replay"


@pytest.fixture(scope="session")
def beta_cik() -> str:
    return os.environ.get("BETA_CIK") or "0003003396"


@pytest.fixture(scope="session")
def beta_ccc() -> str:
    return os.environ.get("BETA_CCC") or "REDACTED"


@pytest.fixture
def beta_client(beta_filer_token: str, beta_user_token: str) -> Client:
    return Client(beta_filer_token, beta_user_token, mode="test", host=BETA_HOST)


def _scrub_request_body(request: object) -> object:
    """Scrub the CCC (filerCcc element) out of recorded submission XML bodies.

    The CCC is per-CIK and acts as a password for the <cor:filerCcc> element
    in the submission envelope. Cassettes commit to the repo so we must not
    leak it. We replace any value inside ``<...filerCcc>...</...filerCcc>``
    with the literal string ``REDACTED``.
    """
    body = getattr(request, "body", None)
    if not body:
        return request
    if isinstance(body, bytes):
        body = re.sub(
            rb"(<[^>]*filerCcc>)([^<]*)(</[^>]*filerCcc>)",
            rb"\1REDACTED\3",
            body,
        )
        request.body = body
    return request


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    # `record_mode` is intentionally omitted so the `--record-mode=once` CLI
    # flag can take effect. Default at replay time (no flag) is "none".
    # Authorization header carries BOTH tokens (filer + user, comma-separated)
    # per the SEC EDGAR API Development Toolkit convention.
    return {
        "filter_headers": [
            ("authorization", "Bearer REDACTED"),
        ],
        "filter_query_parameters": ["token"],
        "before_record_request": _scrub_request_body,
    }
