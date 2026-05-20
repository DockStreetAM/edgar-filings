"""Token types and request-header composition for EDGAR's dual-token auth.

EDGAR requires two JWT bearer tokens for the Submission API and Filer
Management API:

- A **Filer API Token** — created by a Technical Administrator on the EDGAR
  Filer Management dashboard, valid 1 year.
- A **User API Token** — created by an account administrator or user, valid
  30 days.

The SEC OpenAPI spec describes a single ``Authorization: Bearer`` slot
on each operation but the live API requires BOTH tokens for
submission/filer-management endpoints. Per the official SEC EDGAR API
Development Toolkit (``api-bravo.edgarfiling.sec.gov/resources``), the
convention is:

- Single ``Authorization`` header with ``bearer`` prefix.
- When both tokens are present, separate them with ``,`` or a space, with
  the **Filer API Token first** and the **User API Token second**:

    Authorization: bearer <filer_token>,<user_token>

- Operational Status, Submission Status (single + multi) take only the
  filer token.
- Submission API and Filer Management API take both.

If EDGAR responds with an error like *"token 1 is not in the format
expected"* or *"token 2 is not in the format expected"*, the index refers
to position in the comma-separated list, not which JWE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

_T = TypeVar("_T", "FilerToken", "UserToken")


def coerce_token(value: str | _T | None, cls: type[_T]) -> _T | None:
    """Accept a raw JWE string, a typed token, or ``None`` and normalize to the typed form."""
    if value is None:
        return None
    if isinstance(value, cls):
        return value
    return cls(value=value)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class FilerToken:
    """JWT issued to a filer/CIK by a Technical Administrator."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("FilerToken value must be a non-empty string")

    def __repr__(self) -> str:
        return "FilerToken(value='***redacted***')"


@dataclass(frozen=True, slots=True)
class UserToken:
    """JWT issued to an individual EDGAR user (30-day validity)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("UserToken value must be a non-empty string")

    def __repr__(self) -> str:
        return "UserToken(value='***redacted***')"


def build_headers(
    filer: FilerToken,
    user: UserToken | None,
    *,
    login_cik: str | None = None,
    content_type: str | None = None,
) -> dict[str, str]:
    """Compose the request headers for an EDGAR API call.

    ``user`` may be ``None`` for endpoints that only need the filer token
    (operational status, submission status).
    """
    if user is None:
        auth_value = f"Bearer {filer.value}"
    else:
        auth_value = f"Bearer {filer.value},{user.value}"
    headers: dict[str, str] = {
        "Authorization": auth_value,
        "Accept": "application/json",
    }
    if login_cik is not None:
        headers["X-EDGAR-LOGIN-CIK"] = login_cik
    if content_type is not None:
        headers["Content-Type"] = content_type
    return headers
