# Changelog

All notable changes to `edgar-filings` are documented here. Format roughly
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning is
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
- `py.typed` marker (PEP 561) so downstream `mypy` / `pyright` see our type hints.
- 47 tests (44 unit + 3 VCR-replay integration). Cassettes scrub both the
  Authorization header and the CCC inside submission XML bodies.
- GitHub Actions CI on Python 3.10–3.13 across Ubuntu, macOS, Windows.
- Release workflow using PyPI Trusted Publishing (OIDC, no long-lived tokens).

### Known limitations
- **Form 13F is not supported by the EDGAR Submission API.** EDGAR explicitly
  rejects 13F submissions sent through this API with: *"EDGAR no longer accepts
  EDGARLink submissions as an official filing for Form 13F."* 13F filers must
  use the legacy `www.edgarfiling.sec.gov` web upload. See README for details.
