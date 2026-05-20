"""Shared request/response plumbing for the sync and async clients.

The sync ``Client`` and ``AsyncClient`` differ only in which httpx primitive
they call. URL composition, header building, JSON decoding, and error
classification all live here so the two clients can't drift.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from . import errors as err
from ._hosts import Mode, host_for_mode
from .auth import FilerToken, UserToken, build_headers
from .submissions import stamp_live_test_flag

if TYPE_CHECKING:
    from pydantic import BaseModel

    ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(slots=True)
class RequestSpec:
    method: str
    url: str
    headers: dict[str, str]
    content: bytes | None = None
    json_body: Any = None
    params: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ClientConfig:
    filer_token: FilerToken
    user_token: UserToken | None
    mode: Mode
    host: str

    @classmethod
    def build(
        cls,
        filer_token: FilerToken,
        user_token: UserToken | None,
        mode: Mode,
        host: str | None,
    ) -> ClientConfig:
        return cls(
            filer_token=filer_token,
            user_token=user_token,
            mode=mode,
            host=host or host_for_mode(mode),
        )


def build_request(
    cfg: ClientConfig,
    method: str,
    path: str,
    *,
    needs_user_token: bool,
    content: bytes | None = None,
    content_type: str | None = None,
    json_body: Any = None,
    login_cik: str | None = None,
    params: dict[str, str] | None = None,
) -> RequestSpec:
    """Compose a fully-prepared request to an EDGAR endpoint."""
    if needs_user_token and cfg.user_token is None:
        raise err.AuthError(
            "This endpoint requires both a Filer API Token and a User API Token; "
            "user_token is None"
        )

    url = cfg.host.rstrip("/") + path
    headers = build_headers(
        cfg.filer_token,
        cfg.user_token if needs_user_token else None,
        login_cik=login_cik,
        content_type=content_type,
    )
    return RequestSpec(
        method=method,
        url=url,
        headers=headers,
        content=content,
        json_body=json_body,
        params=params,
    )


def parse_response(
    status_code: int,
    body: bytes,
    content_type: str | None,
) -> dict[str, Any] | list[Any] | None:
    """Decode an EDGAR response body into JSON if applicable.

    Raises the appropriate ``EdgarError`` subclass for any 4xx/5xx response.
    """
    parsed: dict[str, Any] | list[Any] | None = None
    if body and content_type and "application/json" in content_type.lower():
        try:
            decoded_any: Any = json.loads(body)
        except json.JSONDecodeError:
            decoded_any = None
        if isinstance(decoded_any, (dict, list)):
            parsed = decoded_any

    if status_code >= 400:
        decoded = parsed if isinstance(parsed, dict) else None
        raise err.from_response(status_code=status_code, body=body, parsed=decoded)

    return parsed


def prepare_submission(
    cfg: ClientConfig, xml: bytes, kind: str, *, confirm_live: bool
) -> tuple[bytes, str]:
    """Validate live-mode confirmation, stamp the LIVE/TEST flag, return (body, path)."""
    if cfg.mode == "live" and not confirm_live:
        raise err.LiveModeNotConfirmed(
            "submit() in mode='live' requires confirm_live=True. "
            "This guard prevents an accidental live filing to SEC EDGAR."
        )
    return stamp_live_test_flag(xml, cfg.mode), f"/submission/{kind}/{cfg.mode}"


def model_from(parsed: Any, model_cls: type[ModelT]) -> ModelT:
    """Validate ``parsed`` against a pydantic model.

    EDGAR sometimes wraps responses in a top-level ``messages`` envelope only
    (e.g., when no data is being returned). We always return *some* model
    instance — empty fields are fine; the typed attributes default sensibly.
    """
    if parsed is None:
        return model_cls.model_validate({})
    if not isinstance(parsed, dict):
        return model_cls.model_validate({"messages": []})
    return model_cls.model_validate(parsed)
