"""Pydantic models for EDGAR API responses.

These models cover the response shapes we surface from the client. We
deliberately use ``extra='allow'`` so the package keeps working when EDGAR
adds new fields between releases — the typed attributes are the contract,
anything extra is reachable via ``model_extra``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MessageType = Literal["INFO", "NOTICE", "WARNING", "ERROR"]
SubmissionModeName = Literal["LIVE", "TEST"]
SubmissionTypeName = Literal["SINGLE", "BULK"]
TransmissionStatusName = Literal["RECEIVED", "REJECTED", "FAILED"]
ProcessingStatusName = Literal[
    "PROCESSING",
    "SUSPENDED",
    "DISSEMINATED",
    "NO_STATUS",
    "BLOCKED",
    "DONE",
    "ACCEPTED",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Message(_Model):
    type: MessageType | None = None
    content: str | None = None


class SEFMessage(Message):
    error_number: int | None = Field(default=None, alias="errorNumber")
    error_label: str | None = Field(default=None, alias="errorLabel")


class _TrackedResponse(_Model):
    tracking: str | None = None
    locator: str | None = None
    messages: list[Message] = Field(default_factory=list)


# Operational status -----------------------------------------------------------


class StatusResponse(_TrackedResponse):
    """Operational status. Spec models ``condition`` as an object but live API
    returns a string (``"ACCEPTING"``, ``"NOT AVAILABLE"``, ``"DOWN"``,
    ``"ACCEPTING AFTER HOURS"``) plus a singular ``message`` field — schema
    drift the OpenAPI spec doesn't reflect.
    """

    condition: str | None = None
    message: str | None = None


# Filer management -------------------------------------------------------------


class FilerInfo(_Model):
    cik: str | None = None
    company_conformed_name: str | None = Field(default=None, alias="companyConformedName")
    state_code: str | None = Field(default=None, alias="stateCode")
    # Any other fields surface via model_extra.


class FilerInfoResponse(_TrackedResponse):
    filer_info: list[FilerInfo] = Field(default_factory=list, alias="filerInfo")


class FilerCheckResponse(_TrackedResponse):
    can_file: bool | None = Field(default=None, alias="canFile")
    confirmation_due_date: str | None = Field(default=None, alias="confirmationDueDate")


class FilerCCCResponse(_TrackedResponse):
    ccc: str | None = None


class IndividualInfo(_Model):
    email: str | None = None
    roles: list[str] = Field(default_factory=list)


class IndividualInfoResponse(_TrackedResponse):
    individuals: list[IndividualInfo] = Field(default_factory=list)


class IndividualRole(_Model):
    """Request payload entry for ``POST /fm/{cik}/individuals`` (add individuals)."""

    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email: str
    in_admin_role: bool = Field(default=False, alias="inAdminRole")
    in_tech_admin_role: bool = Field(default=False, alias="inTechAdminRole")
    in_user_role: bool = Field(default=False, alias="inUserRole")
    middle_name: str | None = Field(default=None, alias="middleName")


class EmailRole(_Model):
    """Request payload entry for ``PUT /fm/{cik}/individuals`` (change roles)."""

    email: str
    in_admin_role: bool = Field(default=False, alias="inAdminRole")
    in_tech_admin_role: bool = Field(default=False, alias="inTechAdminRole")
    in_user_role: bool = Field(default=False, alias="inUserRole")


class UpdateCCC(_Model):
    """Request body for ``PUT /fm/{cik}/ccc`` (set custom CCC).

    Both the current and new CCC are required — EDGAR validates the current
    CCC before applying the change.
    """

    ccc: str
    new_ccc: str = Field(alias="newCCC")


class DelegationInfo(_Model):
    delegator_cik: str | None = Field(default=None, alias="delegatorCik")
    delegate_cik: str | None = Field(default=None, alias="delegateCik")


class DelegationInfoResponse(_TrackedResponse):
    delegations: list[DelegationInfo] = Field(default_factory=list)


# Submission -------------------------------------------------------------------


class SingleSubmissionResponse(_TrackedResponse):
    accession_number: str | None = Field(default=None, alias="accessionNumber")


class SubmissionResponseItem(_TrackedResponse):
    accession_number: str | None = Field(default=None, alias="accessionNumber")


class ListSubmissionResponse(_TrackedResponse):
    submissions: list[SubmissionResponseItem] = Field(default_factory=list)


# Submission status ------------------------------------------------------------


class SingleSubmissionStatusResponse(_TrackedResponse):
    submission_accession_number: str | None = Field(default=None, alias="submissionAccessionNumber")
    submission_form_type: str | None = Field(default=None, alias="submissionFormType")
    items: list[str] = Field(default_factory=list)
    final: bool | None = None
    transmission_status: TransmissionStatusName | None = Field(
        default=None, alias="transmissionStatus"
    )
    processing_status: ProcessingStatusName | None = Field(default=None, alias="processingStatus")
    submission_mode: SubmissionModeName | None = Field(default=None, alias="submissionMode")
    submission_type: SubmissionTypeName | None = Field(default=None, alias="submissionType")


class SubmissionStatusResponseItem(SingleSubmissionStatusResponse):
    pass


class ListSubmissionStatusResponse(_TrackedResponse):
    statuses: list[SubmissionStatusResponseItem] = Field(default_factory=list)


class MultipleAccessionNumberRequest(_Model):
    accession_numbers: list[str] = Field(alias="accessionNumbers")
