"""Sample response payloads modeled after the EDGAR OpenAPI spec examples."""

from __future__ import annotations

STATUS_OK = {
    "tracking": "f0bd5ef3aaf666475b7b466d46120973",
    "locator": "nfkkg",
    "condition": "ACCEPTING",
    "message": "EDGAR is available because EDGAR is reporting that it is operational and within operating hours.",
}

FILER_INFO_OK = {
    "tracking": "f0bd5ef3aaf666475b7b466d46120973",
    "locator": "nfkkg",
    "messages": [{"type": "INFO", "content": "OK"}],
    "filerInfo": [
        {
            "cik": "0000000000",
            "companyConformedName": "Example Co",
            "stateCode": "TX",
        }
    ],
}

FILER_CHECK_OK = {
    "tracking": "trk-1",
    "locator": "loc-1",
    "messages": [{"type": "INFO", "content": "OK"}],
    "canFile": True,
    "confirmationDueDate": "2025-12-31T11:59:59-05:00",
}

SUBMISSION_ACCEPTED = {
    "tracking": "trk-sub-1",
    "locator": "loc-sub-1",
    "accessionNumber": "0001234567-26-000001",
    "messages": [{"type": "INFO", "content": "Submission received."}],
}

SUBMISSION_STATUS_DONE = {
    "tracking": "trk-stat-1",
    "locator": "loc-stat-1",
    "submissionAccessionNumber": "0001234567-26-000001",
    "submissionFormType": "13F-HR",
    "items": [],
    "final": True,
    "transmissionStatus": "RECEIVED",
    "processingStatus": "DONE",
    "submissionMode": "TEST",
    "submissionType": "SINGLE",
    "messages": [],
}

ERROR_401 = {
    "tracking": "trk-err-1",
    "locator": "loc-err-1",
    "messages": [
        {
            "type": "ERROR",
            "content": "Unauthorized. The Filer API Token is not active.",
        }
    ],
}

ERROR_400 = {
    "tracking": "trk-err-2",
    "locator": "loc-err-2",
    "messages": [{"type": "ERROR", "content": "Bad request."}],
}

ERROR_500 = {
    "tracking": "trk-err-3",
    "locator": "loc-err-3",
    "messages": [{"type": "ERROR", "content": "Server error."}],
}
