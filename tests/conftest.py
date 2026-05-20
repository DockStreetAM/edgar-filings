"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

from edgar_filings import BETA_HOST, PROD_HOST, AsyncClient, Client


@pytest.fixture
def beta_host() -> str:
    return BETA_HOST


@pytest.fixture
def prod_host() -> str:
    return PROD_HOST


@pytest.fixture
def test_client() -> Iterator[Client]:
    with Client("filer-jwt", "user-jwt", mode="test") as client:
        yield client


@pytest.fixture
def live_client() -> Iterator[Client]:
    with Client("filer-jwt", "user-jwt", mode="live") as client:
        yield client


@pytest.fixture
async def async_test_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient("filer-jwt", "user-jwt", mode="test") as client:
        yield client
