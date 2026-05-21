# Changelog

All notable changes to `edgar-filings` are documented here. Format roughly
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning is
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-05-20

### Added
- `py.typed` marker (PEP 561) — downstream `mypy` and `pyright` now see the
  type hints shipped with the package. Without this marker, type checkers
  treat the package as untyped regardless of the actual hints in the source.

### Internal (no user-visible change)
- CI matrix expanded to Ubuntu + macOS + Windows × Python 3.10–3.13.
- GitHub Actions bumped to Node 24 compatible majors (`actions/checkout@v6`,
  `astral-sh/setup-uv@v8.1.0`).
- Dependabot config added for weekly action and Python dep bumps.
- `CONTRIBUTING.md` added.
- Integration-test fixture now uses the `Client` context manager, removing a
  spurious `ResourceWarning` during teardown.
- CI integration step no longer swallows failures via `|| true`.

## [0.1.0] - 2026-05-20

Initial release. Published to PyPI as `edgar-filings`.

### Added
- Sync `Client` and `AsyncClient` covering all 18 EDGAR API v1.11.0 endpoints
  (operational status, filer management, single/bulk submission, submission
  status). Verified end-to-end against EDGAR Beta (`api-bravo.edgarfiling.sec.gov`).
- `SubmissionBuilder` for the EDGAR XML submission envelope (form type, filer,
  CCC, LIVE/TEST flag, base64-encoded documents). Form-agnostic, works for any
  EDGARLink-supported form.
- Correct dual-token auth convention from the SEC EDGAR API Development Toolkit:
  single `Authorization: bearer <filer>,<user>` header (filer first, user second),
  not the separate `X-User-Token` header earlier guides suggested.
- `mode='test' | 'live'` with `confirm_live=True` guard on submit calls; XML
  `<liveTestFlag>` rewritten to match mode so URL and envelope can't disagree.
- Typed request models for filer-management endpoints: `IndividualRole`,
  `EmailRole`, `UpdateCCC`.
- Typed exception hierarchy mapping HTTP error responses to `AuthError`,
  `EdgarValidationError`, `EdgarServerError`. Every exception carries the
  `tracking` and `locator` identifiers EDGAR returns.
- 47 tests (44 unit + 3 VCR-replay integration). Cassettes scrub both the
  Authorization header and the CCC inside submission XML bodies.
- GitHub Actions CI on Python 3.10–3.13.
- Release workflow using PyPI Trusted Publishing (OIDC, no long-lived tokens).

### Known limitations
- **Form 13F is not supported by the EDGAR Submission API.** EDGAR explicitly
  rejects 13F submissions sent through this API with: *"EDGAR no longer accepts
  EDGARLink submissions as an official filing for Form 13F."* 13F filers must
  use the legacy `www.edgarfiling.sec.gov` web upload. See README for details.
