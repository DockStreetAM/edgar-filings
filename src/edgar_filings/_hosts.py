"""EDGAR API host constants."""

from __future__ import annotations

from typing import Literal

PROD_HOST = "https://api.edgarfiling.sec.gov"
BETA_HOST = "https://api-bravo.edgarfiling.sec.gov"

Mode = Literal["test", "live"]


def host_for_mode(mode: Mode) -> str:
    if mode == "live":
        return PROD_HOST
    if mode == "test":
        return BETA_HOST
    raise ValueError(f"invalid mode: {mode!r}")
