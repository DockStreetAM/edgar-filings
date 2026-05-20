"""Exception hierarchy for the EDGAR API client.

Every exception carries the ``tracking`` and ``locator`` identifiers EDGAR
returns on error responses; quote them to the EDGAR Help Desk when seeking
support.
"""

from __future__ import annotations

from typing import Any


class EdgarError(Exception):
    """Base class for all errors raised by ``edgar_filings``."""

    def __init__(
        self,
        message: str,
        *,
        tracking: str | None = None,
        locator: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        status_code: int | None = None,
        response_body: bytes | None = None,
    ) -> None:
        super().__init__(message)
        self.tracking = tracking
        self.locator = locator
        self.messages = messages or []
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        base = super().__str__()
        parts = [base]
        if self.status_code is not None:
            parts.append(f"http={self.status_code}")
        if self.tracking:
            parts.append(f"tracking={self.tracking}")
        if self.locator:
            parts.append(f"locator={self.locator}")
        return " ".join(parts)


class AuthError(EdgarError):
    """401 or 403 from EDGAR — token missing, invalid, expired, or not permitted."""


class EdgarValidationError(EdgarError):
    """400 from EDGAR — request body or parameters did not validate."""


class EdgarServerError(EdgarError):
    """5xx from EDGAR — service unavailable or internal error."""


class LiveModeNotConfirmed(EdgarError):
    """Raised when ``mode='live'`` submit is attempted without ``confirm_live=True``."""


def from_response(
    *,
    status_code: int,
    body: bytes,
    parsed: dict[str, Any] | None,
) -> EdgarError:
    """Build the correct exception for an HTTP error response.

    ``parsed`` is the JSON-decoded body if it was JSON, else ``None``.
    """

    tracking = locator = None
    messages: list[dict[str, Any]] = []
    if parsed:
        tracking = parsed.get("tracking")
        locator = parsed.get("locator")
        messages = parsed.get("messages") or []

    summary = _summarize_messages(messages) or f"HTTP {status_code}"

    cls: type[EdgarError]
    if status_code in (401, 403):
        cls = AuthError
    elif status_code == 400:
        cls = EdgarValidationError
    elif status_code >= 500:
        cls = EdgarServerError
    else:
        cls = EdgarError

    return cls(
        summary,
        tracking=tracking,
        locator=locator,
        messages=messages,
        status_code=status_code,
        response_body=body,
    )


def _summarize_messages(messages: list[dict[str, Any]]) -> str | None:
    if not messages:
        return None
    parts = []
    for m in messages:
        t = m.get("type") or "MESSAGE"
        c = m.get("content") or ""
        parts.append(f"[{t}] {c}".strip())
    return " | ".join(parts)
