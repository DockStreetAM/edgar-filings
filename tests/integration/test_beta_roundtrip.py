"""End-to-end tests against EDGAR Beta.

These tests are skipped unless BETA_* env vars are set. CI replays VCR
cassettes from ``tests/integration/cassettes/``; re-record locally with::

    BETA_FILER_TOKEN=... BETA_USER_TOKEN=... BETA_CIK=... \\
        uv run pytest tests/integration/ --record-mode=once

A skeleton 13F-HR is built from ``SubmissionBuilder`` so the integration
test exercises the full round-trip including XML envelope construction.
"""

from __future__ import annotations

import time

import pytest

from edgar_filings import Client, EdgarError, SubmissionBuilder


@pytest.mark.vcr
def test_status(beta_client: Client) -> None:
    resp = beta_client.get_status()
    assert resp.condition is not None


@pytest.mark.vcr
def test_verify_credentials(beta_client: Client, beta_cik: str) -> None:
    resp = beta_client.verify_credentials(beta_cik)
    assert resp.can_file is True


@pytest.mark.vcr
def test_submit_test_13f_and_poll_status(
    beta_client: Client, beta_cik: str, beta_ccc: str
) -> None:
    primary_doc = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b"<edgarSubmission>"
        b"<headerData><filerInfo><filer><credentials>"
        b"<cik>" + beta_cik.encode() + b"</cik></credentials></filer></filerInfo></headerData>"
        b"</edgarSubmission>"
    )
    xml = (
        SubmissionBuilder(
            form_type="13F-HR",
            filer_cik=beta_cik,
            ccc=beta_ccc,
            mode="test",
        )
        .add_flag("confirmingCopyFlag", False)
        .add_flag("returnCopyFlag", False)
        .add_field("periodOfReport", "12-31-2025")
        .add_document("primary_doc.xml", "13F-HR", primary_doc)
        .build()
    )

    sub = beta_client.submit(xml)
    assert sub.accession_number is not None

    # EDGAR's submission-status endpoint is eventually-consistent — it returns
    # 404 for a brief window after a fresh submission while the accession
    # number propagates from the submission service to the status service.
    # Tolerate the 404 here; only fail if we never see a successful response.
    deadline = time.time() + 60
    final = None
    while time.time() < deadline:
        try:
            status = beta_client.get_submission_status(sub.accession_number)
        except EdgarError as exc:
            if exc.status_code == 404:
                time.sleep(2)
                continue
            raise
        if status.final:
            final = status
            break
        time.sleep(2)
    assert final is not None, "submission did not reach final status within 60s"
