# Changelog

All notable changes to `edgar-filings` are documented here. Format roughly
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning is
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Initial sync `Client` and `AsyncClient` covering all 18 EDGAR API endpoints
  (operational status, filer management, single/bulk submission, submission
  status).
- `SubmissionBuilder` for the EDGAR XML submission envelope (form type, filer,
  CCC, LIVE/TEST flag, base64-encoded documents).
- `mode='test' | 'live'` with `confirm_live=True` guard on submit calls.
- Typed exception hierarchy mapping HTTP error responses to
  `AuthError`, `EdgarValidationError`, `EdgarServerError`.
- Unit tests against the OpenAPI spec examples.
- Integration test scaffold targeting `api-bravo.edgarfiling.sec.gov` via VCR.
