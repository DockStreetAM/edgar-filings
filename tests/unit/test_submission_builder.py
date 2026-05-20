from __future__ import annotations

import base64

import pytest
from lxml import etree

from edgar_filings import NS_COM, NS_COR, SubmissionBuilder


def _parse(xml: bytes) -> etree._Element:
    return etree.fromstring(xml)


def _find(root: etree._Element, ns: str, name: str) -> etree._Element | None:
    return root.find(f"{{{ns}}}{name}")


def test_basic_envelope_test_mode() -> None:
    xml = SubmissionBuilder(
        form_type="13F-HR",
        filer_cik="0001234567",
        ccc="$secret",
        mode="test",
    ).build()
    root = _parse(xml)
    assert root.tag == f"{{{NS_COR}}}edgarSubmission"
    assert _find(root, NS_COR, "liveTestFlag").text == "TEST"
    assert _find(root, NS_COR, "submissionType").text == "13F-HR"
    filer = _find(root, NS_COR, "filer")
    assert filer is not None
    assert _find(filer, NS_COR, "filerId").text == "0001234567"
    assert _find(filer, NS_COR, "filerCcc").text == "$secret"


def test_live_mode_stamps_live_flag() -> None:
    xml = SubmissionBuilder("13F-HR", "0001", "$ccc", mode="live").build()
    root = _parse(xml)
    assert _find(root, NS_COR, "liveTestFlag").text == "LIVE"


def test_invalid_mode_rejected() -> None:
    with pytest.raises(ValueError):
        SubmissionBuilder("13F-HR", "0001", "$ccc", mode="hybrid")  # type: ignore[arg-type]


def test_missing_required_fields_rejected() -> None:
    with pytest.raises(ValueError):
        SubmissionBuilder("", "0001", "$ccc", mode="test")
    with pytest.raises(ValueError):
        SubmissionBuilder("13F-HR", "", "$ccc", mode="test")
    with pytest.raises(ValueError):
        SubmissionBuilder("13F-HR", "0001", "", mode="test")


def test_flags_and_fields_appear_in_order() -> None:
    xml = (
        SubmissionBuilder("13F-HR", "0001", "$ccc", mode="test")
        .add_flag("confirmingCopyFlag", False)
        .add_flag("returnCopyFlag", True)
        .add_field("periodOfReport", "12-31-2025")
        .build()
    )
    root = _parse(xml)
    flags = _find(root, NS_COR, "flags")
    assert flags is not None
    assert _find(flags, NS_COM, "confirmingCopyFlag").text == "false"
    assert _find(flags, NS_COM, "returnCopyFlag").text == "true"
    assert _find(root, NS_COR, "periodOfReport").text == "12-31-2025"


def test_add_repeated_emits_wrapped_children() -> None:
    xml = (
        SubmissionBuilder("8-K", "0001", "$ccc", mode="test")
        .add_repeated("items", "item", ["1.01", "2.03"])
        .build()
    )
    root = _parse(xml)
    items = _find(root, NS_COR, "items")
    assert items is not None
    children = list(items)
    assert [c.text for c in children] == ["1.01", "2.03"]


def test_documents_are_base64_encoded() -> None:
    payload = b"hello world"
    xml = (
        SubmissionBuilder("13F-HR", "0001", "$ccc", mode="test")
        .add_document("doc.xml", "13F-HR", payload)
        .build()
    )
    root = _parse(xml)
    docs = _find(root, NS_COR, "documents")
    assert docs is not None
    doc = _find(docs, NS_COM, "document")
    assert _find(doc, NS_COM, "conformedName").text == "doc.xml"
    contents_text = _find(doc, NS_COM, "contents").text
    assert base64.b64decode(contents_text) == payload


def test_add_document_requires_bytes() -> None:
    builder = SubmissionBuilder("13F-HR", "0001", "$ccc", mode="test")
    with pytest.raises(TypeError):
        builder.add_document("doc.xml", "13F-HR", "not bytes")  # type: ignore[arg-type]


def test_filer_form_type_included_when_set() -> None:
    xml = SubmissionBuilder(
        "S-1", "0001", "$ccc", mode="test", filer_form_type="S-1"
    ).build()
    root = _parse(xml)
    filer = _find(root, NS_COR, "filer")
    assert _find(filer, NS_COR, "filerFormType").text == "S-1"
