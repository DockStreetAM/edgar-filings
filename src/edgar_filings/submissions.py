"""Build the EDGAR submission XML envelope.

The Submission API's request body is XML conforming to SEC XSDs in the
``http://www.sec.gov/edgar/coreg`` and ``http://www.sec.gov/edgar/common``
namespaces (the ``coregfee`` namespace is used for fee-bearing forms). The
OpenAPI spec models the body as ``type: string``, so we own all serialization.

This module deliberately stays form-agnostic. The structure documented for
8-K, S-1, and 13F in the spec/examples all fit this shape:

    edgarSubmission
        liveTestFlag                       # LIVE or TEST (stamped from mode)
        flags                              # confirmingCopyFlag, ...
        submissionType                     # e.g. "13F-HR"
        filer
            filerId
            filerCcc
            (filerFormType)
        sros
            sroId (one or more)
        <form-specific fields>
        documents
            document
                conformedName
                conformedDocumentType
                contents (base64)

Form-specific fields are added via ``add_field``; repeated children (like
8-K's ``<items>/<item>...``) via ``add_repeated``.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from ._hosts import Mode

NS_COR = "http://www.sec.gov/edgar/coreg"
NS_COR_FEE = "http://www.sec.gov/edgar/coregfee"
NS_COM = "http://www.sec.gov/edgar/common"
NS_FEEC = "http://www.sec.gov/edgar/feecommon"


def _q(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def _xml_bool(value: bool) -> str:
    return "true" if value else "false"


@dataclass(slots=True)
class _Document:
    name: str
    doc_type: str
    contents: bytes  # raw bytes; base64-encoded at build time


@dataclass(slots=True)
class _Field:
    namespace: str
    name: str
    value: str


@dataclass(slots=True)
class _Repeated:
    parent_ns: str
    parent_name: str
    child_ns: str
    child_name: str
    values: list[str]


@dataclass
class SubmissionBuilder:
    """Compose an EDGAR submission XML envelope.

    ``mode`` is required and stamps ``<liveTestFlag>`` — the LIVE/TEST decision
    cannot be overridden afterwards. The client uses this same mode to pick
    ``/submission/*/live`` vs ``/submission/*/test`` so URL and envelope can't
    disagree.
    """

    form_type: str
    filer_cik: str
    ccc: str
    mode: Mode
    namespace: str = NS_COR
    sros: list[str] = field(default_factory=lambda: ["NONE"])
    filer_form_type: str | None = None
    flags: list[_Field] = field(default_factory=list, init=False)
    fields: list[_Field | _Repeated] = field(default_factory=list, init=False)
    documents: list[_Document] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if not self.form_type:
            raise ValueError("form_type is required")
        if not self.filer_cik:
            raise ValueError("filer_cik is required")
        if not self.ccc:
            raise ValueError("ccc is required")
        if self.mode not in ("test", "live"):
            raise ValueError(f"mode must be 'test' or 'live', got {self.mode!r}")

    # Fluent setters ---------------------------------------------------------

    def add_flag(self, name: str, value: bool, *, namespace: str = NS_COM) -> SubmissionBuilder:
        """Append a child to ``<flags>``."""
        self.flags.append(_Field(namespace, name, _xml_bool(value)))
        return self

    def add_field(
        self,
        name: str,
        value: str | bool,
        *,
        namespace: str | None = None,
    ) -> SubmissionBuilder:
        """Append a form-specific element between filer/sros and documents."""
        ns = namespace if namespace is not None else self.namespace
        text = _xml_bool(value) if isinstance(value, bool) else str(value)
        self.fields.append(_Field(ns, name, text))
        return self

    def add_repeated(
        self,
        parent: str,
        child: str,
        values: list[str],
        *,
        parent_namespace: str | None = None,
        child_namespace: str | None = None,
    ) -> SubmissionBuilder:
        """Append a wrapper element containing repeated children.

        E.g. ``add_repeated("items", "item", ["1.01", "2.03"])`` produces::

            <cor:items>
                <cor:item>1.01</cor:item>
                <cor:item>2.03</cor:item>
            </cor:items>
        """
        pns = parent_namespace if parent_namespace is not None else self.namespace
        cns = child_namespace if child_namespace is not None else self.namespace
        self.fields.append(_Repeated(pns, parent, cns, child, list(values)))
        return self

    def add_document(self, name: str, doc_type: str, contents: bytes) -> SubmissionBuilder:
        """Attach a document to the submission. ``contents`` is base64-encoded at build time."""
        if not isinstance(contents, (bytes, bytearray)):
            raise TypeError("contents must be bytes")
        self.documents.append(_Document(name=name, doc_type=doc_type, contents=bytes(contents)))
        return self

    # Serialization ----------------------------------------------------------

    def build(self) -> bytes:
        """Produce the XML envelope as UTF-8 bytes."""
        nsmap = {"cor": self.namespace, "com": NS_COM}
        root = etree.Element(_q(self.namespace, "edgarSubmission"), nsmap=nsmap)

        live_test = etree.SubElement(root, _q(self.namespace, "liveTestFlag"))
        live_test.text = "LIVE" if self.mode == "live" else "TEST"

        flags_el = etree.SubElement(root, _q(self.namespace, "flags"))
        for f in self.flags:
            child = etree.SubElement(flags_el, _q(f.namespace, f.name))
            child.text = f.value

        st = etree.SubElement(root, _q(self.namespace, "submissionType"))
        st.text = self.form_type

        filer_el = etree.SubElement(root, _q(self.namespace, "filer"))
        fid = etree.SubElement(filer_el, _q(self.namespace, "filerId"))
        fid.text = self.filer_cik
        fccc = etree.SubElement(filer_el, _q(self.namespace, "filerCcc"))
        fccc.text = self.ccc
        if self.filer_form_type is not None:
            fft = etree.SubElement(filer_el, _q(self.namespace, "filerFormType"))
            fft.text = self.filer_form_type

        sros_el = etree.SubElement(root, _q(self.namespace, "sros"))
        for sro in self.sros:
            s = etree.SubElement(sros_el, _q(NS_COM, "sroId"))
            s.text = sro

        for item in self.fields:
            if isinstance(item, _Field):
                el = etree.SubElement(root, _q(item.namespace, item.name))
                el.text = item.value
            else:
                parent = etree.SubElement(root, _q(item.parent_ns, item.parent_name))
                for v in item.values:
                    c = etree.SubElement(parent, _q(item.child_ns, item.child_name))
                    c.text = v

        if self.documents:
            docs_el = etree.SubElement(root, _q(self.namespace, "documents"))
            for d in self.documents:
                de = etree.SubElement(docs_el, _q(NS_COM, "document"))
                cn = etree.SubElement(de, _q(NS_COM, "conformedName"))
                cn.text = d.name
                ct = etree.SubElement(de, _q(NS_COM, "conformedDocumentType"))
                ct.text = d.doc_type
                cs = etree.SubElement(de, _q(NS_COM, "contents"))
                cs.text = base64.b64encode(d.contents).decode("ascii")

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=False)


def stamp_live_test_flag(xml_bytes: bytes, mode: Mode) -> bytes:
    """Force ``<liveTestFlag>`` in an existing envelope to match ``mode``.

    This is the safety rail that prevents URL/body disagreement: even if a
    caller hand-built XML with the wrong flag, the client rewrites it before
    sending. The element is matched by local-name in any namespace so this
    works for the ``coreg``, ``coregfee``, and any future variants.

    Raises ``ValueError`` if the input is not valid XML or has no
    ``liveTestFlag`` element.
    """
    desired = "LIVE" if mode == "live" else "TEST"
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"submission body is not valid XML: {exc}") from exc

    found = _find_local(root, "liveTestFlag")
    if found is None:
        raise ValueError("submission body is missing <liveTestFlag>")
    if found.text != desired:
        found.text = desired
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=False)


def _find_local(root: Any, local_name: str) -> Any:
    """Find the first descendant element with the given local-name in any namespace."""
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        tag = el.tag
        if tag.startswith("{"):
            tag = tag.split("}", 1)[1]
        if tag == local_name:
            return el
    return None
