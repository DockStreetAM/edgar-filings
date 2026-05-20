"""Python client for the SEC EDGAR filing APIs.

See https://github.com/Dockstreet/edgar-filings for documentation.

Quickstart::

    from edgar_filings import Client, SubmissionBuilder

    with Client(filer_token, user_token, mode="test") as client:
        # Verify credentials against the fictitious beta CIK
        check = client.verify_credentials("0001234567")
        assert check.can_file

        # Build and submit a 13F-HR in TEST mode (api-bravo)
        xml = (
            SubmissionBuilder(
                form_type="13F-HR",
                filer_cik="0001234567",
                ccc="$secret",
                mode="test",
            )
            .add_flag("confirmingCopyFlag", False)
            .add_field("periodOfReport", "12-31-2025")
            .add_document("primary_doc.xml", "13F-HR", b"<?xml ...?>")
            .build()
        )
        response = client.submit(xml)
        print(response.accession_number)
"""

from __future__ import annotations

from .__version__ import __version__
from ._hosts import BETA_HOST, PROD_HOST, Mode
from .async_client import AsyncClient
from .auth import FilerToken, UserToken
from .client import Client
from .errors import (
    AuthError,
    EdgarError,
    EdgarServerError,
    EdgarValidationError,
    LiveModeNotConfirmed,
)
from .models import EmailRole, IndividualRole, UpdateCCC
from .submissions import (
    NS_COM,
    NS_COR,
    NS_COR_FEE,
    NS_FEEC,
    SubmissionBuilder,
    stamp_live_test_flag,
)

__all__ = [
    "BETA_HOST",
    "NS_COM",
    "NS_COR",
    "NS_COR_FEE",
    "NS_FEEC",
    "PROD_HOST",
    "AsyncClient",
    "AuthError",
    "Client",
    "EdgarError",
    "EdgarServerError",
    "EdgarValidationError",
    "EmailRole",
    "FilerToken",
    "IndividualRole",
    "LiveModeNotConfirmed",
    "Mode",
    "SubmissionBuilder",
    "UpdateCCC",
    "UserToken",
    "__version__",
    "stamp_live_test_flag",
]
