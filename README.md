# edgar-filings

Python client for the SEC EDGAR filing APIs — operational status, filer
management, single and bulk submission, and submission status. Built around
the EDGAR API v1.11.0 OpenAPI spec, with corrections for the dual-token auth
convention and live-API schema drift that the published spec doesn't reflect.

> **This package can submit live filings to the SEC.** Read the [LIVE vs TEST
> mode](#live-vs-test-mode) section before using it against production.

## Status

- ✅ All 18 EDGAR API v1.11.0 endpoints covered by sync `Client` and async `AsyncClient`.
- ✅ End-to-end verified against EDGAR Beta (`api-bravo.edgarfiling.sec.gov`)
  on 2026-05-20: `GET /status`, `GET /fm/{cik}/verify`,
  `POST /submission/single/test`, and the submission-status polling lifecycle.
- ✅ Mode-safety rails (`confirm_live=True` guard + XML `<liveTestFlag>`
  rewriting) verified.
- ✅ 47 tests (44 unit + 3 integration with VCR cassette replay), ruff clean,
  mypy strict clean.
- ⚠ **Form 13F is NOT supported by the EDGAR Submission API.** See
  [Form support](#form-support) below. The package works for any form
  EDGAR's EDGARLink XML envelope supports (8-K, 10-K, S-1, etc.).

## Install

```bash
pip install edgar-filings
# or
uv add edgar-filings
```

## Quickstart

```python
from edgar_filings import Client, SubmissionBuilder

# Beta tokens, fictitious CIK, test endpoint — safe to run.
with Client(filer_token, user_token, mode="test") as client:
    check = client.verify_credentials(beta_cik)
    assert check.can_file

    xml = (
        SubmissionBuilder(
            form_type="8-K",
            filer_cik=beta_cik,
            ccc="$secret",
            mode="test",
        )
        .add_flag("confirmingCopyFlag", False)
        .add_field("emergingGrowthCompanyFlag", True)
        .add_repeated("items", "item", ["1.01"])
        .add_document("file.txt", "8-K", b"<event report contents>")
        .build()
    )

    submission = client.submit(xml)
    print(submission.accession_number)
```

Async usage is symmetric:

```python
from edgar_filings import AsyncClient

async with AsyncClient(filer_token, user_token, mode="test") as client:
    status = await client.get_status()
    print(status.condition)  # "ACCEPTING", "NOT AVAILABLE", "DOWN", ...
```

## Form support

EDGAR's Submission API accepts a single XML envelope format (internally called
**EDGARLink**, defined by the SEC XSDs in the
`http://www.sec.gov/edgar/coreg` namespace or `coregfee` for fee-bearing
forms). This package builds and transmits that envelope.

### Forms confirmed to work via this API

Per the SEC OpenAPI spec examples and the EDGARLink XSDs, the API accepts
the great majority of EDGAR submission types via EDGARLink — including
8-K, 10-K, 10-Q, S-1 (and its fee-bearing variants), 20-F, 6-K, DEF 14A,
and most current-report / registration / periodic-report families.

The `SubmissionBuilder` is form-agnostic: you supply form-specific elements
via `add_field`, `add_flag`, and `add_repeated`. The wire format is XML, so
any form whose EDGARLink XSD is documented in the EDGAR Filer Manual Volume
II works.

### Forms NOT supported via this API

| Form family                                   | Why                                                | Where to file                                                                    |
|-----------------------------------------------|----------------------------------------------------|----------------------------------------------------------------------------------|
| **Form 13F** (13F-HR, 13F-HR/A, 13F-NT, 13F-NT/A, 13F-CTR, 13F-CTR/A) | EDGAR explicitly rejects 13F submissions sent through this API with: *"EDGAR no longer accepts EDGARLink submissions as an official filing for Form 13F."* | `https://www.edgarfiling.sec.gov` (legacy EDGAR Filing Website) — accepts filer-constructed 13F XML uploads per the EDGAR Form 13F XML Technical Specification, browser/cookie auth only |
| Ownership filings (Forms 3, 4, 5, 144)        | Moved to EDGAR Online Forms                        | `https://www.onlineforms.edgarfiling.sec.gov`                                    |
| Schedule 13D / 13G                            | Moved to EDGAR Online Forms                        | `https://www.onlineforms.edgarfiling.sec.gov`                                    |
| Form D                                        | Moved to EDGAR Online Forms                        | `https://www.onlineforms.edgarfiling.sec.gov`                                    |

**On Form 13F specifically:** as of 2026-05-20, there is no announced SEC
roadmap item to migrate 13F to the EDGAR Submission API. Verified against
EDGAR Release 26.0.1 (Feb 2026), Release 26.1 (March 2026), EDGAR Filer
Manual Volume II (March 2026), the EDGAR Form 13F XML Technical
Specification v1.9 (current) and draft v1.6, and EDGAR Beta release notes.
If you need programmatic 13F filing today the realistic options are
browser automation against the legacy filing website, or a commercial
filing-agent service.

## Authentication

The EDGAR APIs require two JWE bearer tokens, both minted from the EDGAR
Filer Management dashboard:

- **Filer API Token** — issued by a Technical Administrator. Valid 1 year.
  Required by every endpoint. Encodes the CIK in its JWE header.
- **User API Token** — issued by an account administrator or user.
  Valid 30 days; creating a new one auto-invalidates any prior token for
  that user. Required by `/submission/*` and all `/fm/*` endpoints; NOT
  required by `/status` or the submission-status endpoints.

How `edgar-filings` transmits them — per the official SEC
[EDGAR API Development Toolkit](https://api-bravo.edgarfiling.sec.gov/resources)
("Authentication / Authorize" section): both tokens ride in the **same**
`Authorization` header, comma-separated, **filer first, user second**:

```
Authorization: Bearer <filer_token>,<user_token>
```

The OpenAPI spec models this as a single `http: bearer` scheme — the
two-token format is not directly representable in OpenAPI 3.1 syntax,
which is why early implementations (and an earlier version of this
package) mistakenly used a separate `X-User-Token` header. The Toolkit
page is authoritative.

EDGAR error responses identify a misbehaving token by position in this
list — *"token 1 of type FILER_API ..."* (the filer JWE) or
*"token 2 of type USER_API ..."* (the user JWE).

## LIVE vs TEST mode

EDGAR exposes parallel `/submission/*/test` and `/submission/*/live` endpoints
on the same hosts, but also runs an entirely separate beta environment at
`api-bravo.edgarfiling.sec.gov` for filers to exercise the API without
touching production filings.

`Client(mode=...)` controls both:

| `mode`  | Default host                            | Submission path        | `<liveTestFlag>` |
|---------|-----------------------------------------|------------------------|------------------|
| `test`  | `https://api-bravo.edgarfiling.sec.gov` | `/submission/*/test`   | `TEST`           |
| `live`  | `https://api.edgarfiling.sec.gov`       | `/submission/*/live`   | `LIVE`           |

Three guardrails:

1. `Client(mode='live').submit(xml)` raises `LiveModeNotConfirmed` unless
   you also pass `confirm_live=True`. Pass it explicitly per call.
2. Before send, the XML body's `<liveTestFlag>` is rewritten to match the
   client's mode. URL and envelope cannot disagree.
3. Successful live submissions emit a `WARNING` log under the
   `edgar_filings` logger with the accession number and tracking ID.

To intentionally hit beta endpoints from a `mode='live'` client (or vice
versa), pass `host=` explicitly.

## Setting up an EDGAR Beta account

EDGAR Beta is the safe testing environment. Production tokens won't work
against Beta and vice versa — each environment mints its own tokens.

1. Create Login.gov credentials at https://login.gov using the email
   address you want EDGAR to know you by (it's visible to other filers on
   the dashboard).
2. Sign into Beta Filer Management at
   https://filermanagement-bravo.edgarfiling.sec.gov/.
3. *Apply for EDGAR Access → New EDGAR account* → submit a **test Form
   ID** to create a fictitious CIK. Do NOT use the "Existing EDGAR CIK"
   path; it's intended for narrow recovery scenarios and is destructive
   to the existing dashboard state.
4. **Bootstrap the admin roles.** Beta auto-assigns you Account
   Administrator, but EDGAR requires **at least 2 Account Administrators
   AND at least 2 Technical Administrators** on the CIK before any Filer
   API Token can be minted (separation-of-duties). Order matters:
   - As the sole AA, *Manage Individuals → Add Individual* with role
     **Account Administrator** — invite a teammate or a second Login.gov
     account you control. Wait for them to accept; the entry must show
     *Active* on the dashboard.
   - With 2 AAs, *Manage Individuals → ellipsis → Edit individual role(s)*
     on yourself — **keep Account Administrator checked AND add Technical
     Administrator**. The Edit dialog REPLACES the role set, so unchecking
     AA while checking TA would drop AA count below 2 and fail with
     *"current account administrators count (1) is less than required
     account administrators count (2)."*
   - Repeat for the second person until at least 2 Technical
     Administrators exist.
5. As Technical Administrator → *Manage Filer API Token → Create New Filer
   API Token* (valid 1 year; the tile is greyed out until both quorums are
   met). Copy the token from the success modal — it is shown only once.
6. As account administrator/user → *My User API Token → Create User API
   Token* (valid 30 days; creating a new one auto-invalidates the old).
7. Also note the **CCC** (CIK Confirmation Code) under *Manage CCC* —
   it's a per-CIK password that goes into the submission XML envelope.

Store all four (filer token, user token, fictitious CIK, CCC) somewhere
secure — they are testing-only and never persist outside Beta, but you
don't want them committed to a public repo.

The SEC's *EDGAR Next Filer Testing Guidance* PDF is the authoritative
reference for the above flow.

## API coverage

All 18 endpoints from the EDGAR API v1.11.0 OpenAPI spec are exposed:

- `get_status()` — `GET /status`
- `view_filer(cik)`, `verify_credentials(cik)` — `GET /fm/{cik}[/verify]`
- `generate_ccc(cik)`, `set_custom_ccc(cik, ccc)` — `POST/PUT /fm/{cik}/ccc`
- `view_delegations(cik)`, `send_delegation_invitations(...)`,
  `request_delegation_invitations(...)` — `GET/POST /fm/{cik}/delegations*`
- `view_individuals(cik)`, `add_individuals(...)`, `change_roles(...)`,
  `remove_individuals(...)` — `GET/POST/PUT/DELETE /fm/{cik}/individuals`
- `submit(xml, ...)`, `submit_bulk(xml, ...)` — `POST /submission/{single|bulk}/{live|test}`
- `get_submission_status(accession)`, `get_submission_statuses([accessions])` —
  `GET /submission/{accession}/status`, `POST /submission/status`

Errors map to typed exceptions:

| HTTP    | Exception              |
|---------|------------------------|
| 400     | `EdgarValidationError` |
| 401/403 | `AuthError`            |
| 5xx     | `EdgarServerError`     |

All exceptions carry the `tracking` and `locator` identifiers EDGAR returns;
quote them when seeking support from the EDGAR Help Desk.

### Known live-API schema drift

The OpenAPI spec doesn't exactly match what the production API returns.
Pydantic models in this package use `extra='allow'` so extra fields are
preserved on `model_extra`.

- `GET /status` returns `condition` as a **string** (`"ACCEPTING"`,
  `"NOT AVAILABLE"`, `"DOWN"`, `"ACCEPTING AFTER HOURS"`), not the
  spec's object with `state`/`description`. Response also includes a
  singular `message` field instead of the spec's `messages` array.
- `GET /submission/{accession}/status` returns enums in **UPPERCASE**
  (`"PROCESSING"`, `"DISSEMINATED"`, `"ACCEPTED"`, `"SUSPENDED"`, ...)
  and includes extra fields not in the spec: `submissionProcessingStatus`,
  `transmissionStatus`, `mode`, `documentCount`, `receivedDate`,
  `suspendedDate`, `notification` (base64-encoded human-readable EDGAR
  email body).
- `GET /fm/{cik}/verify` returns `filerApiTokenExpirationDate` and
  `userApiTokenExpirationDate` (not in the spec) alongside the documented
  `canFile` and `confirmationDueDate`.
- Submission-status endpoints **return 404 for a brief window** (~2-4s)
  after a fresh submission, before EDGAR propagates the accession number
  from the submission service to the status service. Treat 404 as
  "not yet, retry" inside any polling loop.

### Submission lifecycle

A successful submission returns HTTP 202 with `transmissionStatus`
`RECEIVED` and an accession number. EDGAR then processes the filing
asynchronously; poll `GET /submission/{accession}/status` until
`final: true`. Terminal states:

| `submissionProcessingStatus` | Meaning                                      |
|------------------------------|----------------------------------------------|
| `ACCEPTED`                   | EDGAR accepted the filing.                   |
| `DISSEMINATED`               | Accepted + publicly disseminated.            |
| `SUSPENDED`                  | Rejected during processing. See `notification` (base64) for human-readable reason. |
| `DONE`                       | EDGAR finished processing; check sub-status. |
| `BLOCKED`                    | Awaiting further action.                     |

## Building submissions

`SubmissionBuilder` produces the EDGAR XML envelope. It deliberately doesn't
ship typed builders for individual forms — there are too many, and they
change. You provide form-specific fields directly:

```python
xml = (
    SubmissionBuilder(
        form_type="8-K",
        filer_cik="0001234567",
        ccc="$secret",
        mode="test",
    )
    .add_flag("confirmingCopyFlag", False)
    .add_flag("returnCopyFlag", False)
    .add_repeated("items", "item", ["1.01", "2.03"])   # 8-K specific
    .add_document("primary_doc.xml", "8-K", primary_doc_bytes)
    .build()
)
```

If you have a pre-built XML envelope (for example produced by another
toolchain), call `client.submit(xml)` directly — the client will still rewrite
`<liveTestFlag>` to match its mode.

## Development

```bash
uv sync --extra dev
uv run pytest tests/unit -q          # 44 fast unit tests, no network
uv run pytest tests/integration -q   # 3 cassette-replay tests, no network
uv run ruff check src tests
uv run mypy src/edgar_filings
```

### Recording integration cassettes

Integration tests in `tests/integration/` are replayed from VCR cassettes
in CI. To re-record against EDGAR Beta, populate a local `.env` from
`.env.example` with `BETA_FILER_TOKEN`, `BETA_USER_TOKEN`, `BETA_CIK`,
`BETA_CCC`, then:

```bash
set -a; source .env; set +a
uv run pytest tests/integration --record-mode=once
```

Cassettes scrub:

- The combined `Authorization` header (both tokens).
- The `<cor:filerCcc>` element inside any submission XML body.

`.env` is gitignored. Tokens never appear in committed cassettes.

## License

MIT — see [LICENSE](LICENSE).
