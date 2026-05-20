# Contributing

Thanks for your interest in `edgar-filings`. The codebase is small — under
1500 lines including tests — so contributions are easy to land.

## Local setup

```bash
git clone https://github.com/DockStreetAM/edgar-filings.git
cd edgar-filings
uv sync --extra dev
```

## Running tests

```bash
uv run pytest tests/unit -q          # 44 fast tests, no network
uv run pytest tests/integration -q   # 3 VCR-replay tests, no network
uv run ruff check src tests
uv run mypy src/edgar_filings
```

## Recording new integration cassettes

The integration tests in `tests/integration/` are replayed from VCR cassettes
in `tests/integration/cassettes/`. To add a new test or re-record an existing
cassette against EDGAR Beta:

1. Set up an EDGAR Beta account per the README's "Setting up an EDGAR Beta
   account" section. You'll need a fictitious Beta CIK plus filer + user API
   tokens.
2. Copy `.env.example` to `.env` and fill in `BETA_FILER_TOKEN`,
   `BETA_USER_TOKEN`, `BETA_CIK`, `BETA_CCC`.
3. Re-record:

   ```bash
   set -a; source .env; set +a
   uv run pytest tests/integration --record-mode=once
   ```

4. Verify no JWE strings or the CCC value leaked into the new cassette:

   ```bash
   grep -E "eyJ|<your_ccc_value>" tests/integration/cassettes/**/*.yaml && echo LEAK
   ```

   The vcr_config in `tests/integration/conftest.py` scrubs the
   `Authorization` header and the `<cor:filerCcc>` element in request bodies
   before writing. If a new endpoint puts secrets in a different field,
   extend `_scrub_request_body`.

## Pull request guidelines

- Keep PRs focused — one concern per PR.
- All checks must pass: `pytest`, `ruff check`, `mypy --strict`.
- For new endpoints or response-shape changes, add a unit test seeded from
  the OpenAPI spec example in `docs/openapi.json`.
- If you change response parsing, also bump the affected pydantic model and
  ensure `extra='allow'` is preserved on the model — EDGAR adds fields between
  releases and `extra='allow'` keeps the client working through that drift.

## Reporting bugs

Every `EdgarError` carries `tracking` and `locator` IDs from EDGAR's response.
Include both in any bug report so the EDGAR Help Desk can correlate.

## Releasing (maintainers)

1. Bump the version in both `src/edgar_filings/__version__.py` and
   `pyproject.toml`.
2. Update `CHANGELOG.md` — move `[Unreleased]` entries under a new versioned
   section with the date.
3. Commit and tag:

   ```bash
   git commit -am "vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

4. The `Release` workflow on tag push builds and publishes to PyPI via Trusted
   Publishing (OIDC, no long-lived tokens). Verify at
   https://pypi.org/project/edgar-filings/ within a minute.
