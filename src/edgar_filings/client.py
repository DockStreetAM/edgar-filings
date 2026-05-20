"""Synchronous EDGAR API client."""

from __future__ import annotations

import logging
import warnings
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from ._base import (
    ClientConfig,
    RequestSpec,
    build_request,
    model_from,
    parse_response,
    prepare_submission,
)
from ._hosts import Mode
from .auth import FilerToken, UserToken, coerce_token
from .models import (
    DelegationInfoResponse,
    EmailRole,
    FilerCCCResponse,
    FilerCheckResponse,
    FilerInfoResponse,
    IndividualInfoResponse,
    IndividualRole,
    ListSubmissionResponse,
    ListSubmissionStatusResponse,
    SingleSubmissionResponse,
    SingleSubmissionStatusResponse,
    StatusResponse,
    UpdateCCC,
)

logger = logging.getLogger("edgar_filings")

_M = TypeVar("_M", bound=BaseModel)


class Client(AbstractContextManager["Client"]):
    """Synchronous client for the SEC EDGAR filing APIs.

    Construction picks the EDGAR host from ``mode``: ``'test'`` →
    api-bravo.edgarfiling.sec.gov (Beta), ``'live'`` →
    api.edgarfiling.sec.gov (production). Pass ``host=`` to override.

    Live submissions require ``confirm_live=True`` on every ``submit()`` call.
    """

    def __init__(
        self,
        filer_token: str | FilerToken,
        user_token: str | UserToken | None = None,
        *,
        mode: Mode = "test",
        host: str | None = None,
        http: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        ft = coerce_token(filer_token, FilerToken)
        if ft is None:
            raise ValueError("filer_token is required")
        ut = coerce_token(user_token, UserToken)
        self._cfg = ClientConfig.build(filer_token=ft, user_token=ut, mode=mode, host=host)
        self._owned_http = http is None
        self._http = http or httpx.Client(timeout=timeout)

    # Context manager --------------------------------------------------------

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._owned_http and not self._http.is_closed:
            self._http.close()

    def __del__(self) -> None:
        # Warn if an owned httpx client was never closed — connections would
        # otherwise leak until garbage collection. Mirrors httpx's own behavior
        # when a Client is GC'd while still open.
        http = getattr(self, "_http", None)
        if getattr(self, "_owned_http", False) and http is not None and not http.is_closed:
            warnings.warn(
                "edgar_filings.Client was garbage-collected without close(). "
                "Use it as a context manager or call client.close() explicitly.",
                ResourceWarning,
                stacklevel=2,
            )
            http.close()

    # Properties -------------------------------------------------------------

    @property
    def mode(self) -> Mode:
        return self._cfg.mode

    @property
    def host(self) -> str:
        return self._cfg.host

    # Operational status -----------------------------------------------------

    def get_status(self) -> StatusResponse:
        spec = build_request(self._cfg, "GET", "/status", needs_user_token=False)
        return model_from(self._send(spec), StatusResponse)

    # Filer management -------------------------------------------------------

    def view_filer(self, cik: str) -> FilerInfoResponse:
        spec = build_request(self._cfg, "GET", f"/fm/{cik}", needs_user_token=True)
        return model_from(self._send(spec), FilerInfoResponse)

    def verify_credentials(self, cik: str) -> FilerCheckResponse:
        spec = build_request(self._cfg, "GET", f"/fm/{cik}/verify", needs_user_token=True)
        return model_from(self._send(spec), FilerCheckResponse)

    def generate_ccc(self, cik: str) -> FilerCCCResponse:
        spec = build_request(self._cfg, "POST", f"/fm/{cik}/ccc", needs_user_token=True)
        return model_from(self._send(spec), FilerCCCResponse)

    def set_custom_ccc(self, cik: str, current_ccc: str, new_ccc: str) -> FilerCCCResponse:
        """Update the CCC for a filer. EDGAR requires the current CCC for verification."""
        body = UpdateCCC(ccc=current_ccc, newCCC=new_ccc).model_dump(by_alias=True)
        return self._json_call("PUT", f"/fm/{cik}/ccc", body, FilerCCCResponse)

    def view_delegations(self, cik: str) -> DelegationInfoResponse:
        return self._get(f"/fm/{cik}/delegations", DelegationInfoResponse)

    def send_delegation_invitations(
        self, cik: str, delegate_ciks: list[str]
    ) -> DelegationInfoResponse:
        return self._json_call(
            "POST", f"/fm/{cik}/delegations", list(delegate_ciks), DelegationInfoResponse
        )

    def request_delegation_invitations(
        self, cik: str, delegator_ciks: list[str]
    ) -> DelegationInfoResponse:
        return self._json_call(
            "POST",
            f"/fm/{cik}/delegationRequests",
            list(delegator_ciks),
            DelegationInfoResponse,
        )

    def view_individuals(self, cik: str) -> IndividualInfoResponse:
        return self._get(f"/fm/{cik}/individuals", IndividualInfoResponse)

    def add_individuals(
        self, cik: str, individuals: list[IndividualRole]
    ) -> IndividualInfoResponse:
        body = [i.model_dump(by_alias=True, exclude_none=True) for i in individuals]
        return self._json_call("POST", f"/fm/{cik}/individuals", body, IndividualInfoResponse)

    def change_roles(self, cik: str, changes: list[EmailRole]) -> IndividualInfoResponse:
        body = [c.model_dump(by_alias=True) for c in changes]
        return self._json_call("PUT", f"/fm/{cik}/individuals", body, IndividualInfoResponse)

    def remove_individuals(self, cik: str, emails: list[str]) -> IndividualInfoResponse:
        return self._json_call(
            "DELETE", f"/fm/{cik}/individuals", list(emails), IndividualInfoResponse
        )

    # Submissions ------------------------------------------------------------

    def submit(
        self,
        xml: bytes,
        *,
        confirm_live: bool = False,
        login_cik: str | None = None,
    ) -> SingleSubmissionResponse:
        """Submit a SINGLE filing.

        Routes to ``/submission/single/{test|live}`` based on the client's
        ``mode``. Live mode requires ``confirm_live=True`` (raises
        :class:`LiveModeNotConfirmed` otherwise).

        The body is parsed, ``<liveTestFlag>`` is forced to match ``mode``
        (so URL and envelope cannot disagree), and the resulting bytes are
        POSTed as ``application/xml``.
        """
        body, path = prepare_submission(self._cfg, xml, "single", confirm_live=confirm_live)
        spec = build_request(
            self._cfg,
            "POST",
            path,
            needs_user_token=True,
            content=body,
            content_type="application/xml",
            login_cik=login_cik,
        )
        parsed = self._send(spec)
        response = model_from(parsed, SingleSubmissionResponse)
        if self._cfg.mode == "live" and response.accession_number:
            logger.warning(
                "edgar live submission accepted accession=%s tracking=%s",
                response.accession_number,
                response.tracking,
            )
        return response

    def submit_bulk(
        self,
        xml: bytes,
        *,
        confirm_live: bool = False,
        login_cik: str | None = None,
    ) -> ListSubmissionResponse:
        body, path = prepare_submission(self._cfg, xml, "bulk", confirm_live=confirm_live)
        spec = build_request(
            self._cfg,
            "POST",
            path,
            needs_user_token=True,
            content=body,
            content_type="application/xml",
            login_cik=login_cik,
        )
        return model_from(self._send(spec), ListSubmissionResponse)

    def get_submission_status(self, accession_number: str) -> SingleSubmissionStatusResponse:
        spec = build_request(
            self._cfg,
            "GET",
            f"/submission/{accession_number}/status",
            needs_user_token=False,
        )
        return model_from(self._send(spec), SingleSubmissionStatusResponse)

    def get_submission_statuses(
        self, accession_numbers: list[str]
    ) -> ListSubmissionStatusResponse:
        if not 1 <= len(accession_numbers) <= 25:
            raise ValueError("accession_numbers must have between 1 and 25 entries per the spec")
        spec = build_request(
            self._cfg,
            "POST",
            "/submission/status",
            needs_user_token=False,
            json_body={"accessionNumbers": list(accession_numbers)},
            content_type="application/json",
        )
        return model_from(self._send(spec), ListSubmissionStatusResponse)

    # Internals --------------------------------------------------------------

    def _get(self, path: str, model_cls: type[_M]) -> _M:
        spec = build_request(self._cfg, "GET", path, needs_user_token=True)
        return model_from(self._send(spec), model_cls)

    def _json_call(self, method: str, path: str, body: Any, model_cls: type[_M]) -> _M:
        spec = build_request(
            self._cfg,
            method,
            path,
            needs_user_token=True,
            json_body=body,
            content_type="application/json",
        )
        return model_from(self._send(spec), model_cls)

    def _send(self, spec: RequestSpec) -> Any:
        kwargs: dict[str, Any] = {
            "method": spec.method,
            "url": spec.url,
            "headers": spec.headers,
        }
        if spec.content is not None:
            kwargs["content"] = spec.content
        if spec.json_body is not None:
            kwargs["json"] = spec.json_body
        if spec.params is not None:
            kwargs["params"] = spec.params
        response = self._http.request(**kwargs)
        return parse_response(
            response.status_code,
            response.content,
            response.headers.get("content-type"),
        )
