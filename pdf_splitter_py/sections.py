from __future__ import annotations

import re

from .types import SectionGroup, SectionKind

PATTERNS: list[tuple[SectionKind, re.Pattern[str]]] = [
    (
        "cover",
        re.compile(
            r"^(front\s*matter|cover|title\s*page|half[-\s]?title|frontispiece|colophon|imprint|copyright)\b",
            re.IGNORECASE,
        ),
    ),
    ("dedication", re.compile(r"^(dedication|epigraph)\b", re.IGNORECASE)),
    ("abstract", re.compile(r"^(abstract|summary|executive\s+summary|synopsis)\b", re.IGNORECASE)),
    ("acknowledgements", re.compile(r"^(acknowledge?ments?|thanks|credits)\b", re.IGNORECASE)),
    ("contents", re.compile(r"^(table\s+of\s+contents|contents|toc)\b", re.IGNORECASE)),
    (
        "figures",
        re.compile(
            r"^(table\s+of\s+figures|list\s+of\s+(figures|tables|plates|illustrations|maps|charts|abbreviations|symbols|acronyms|nomenclature))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "preface",
        re.compile(r"^(preface|foreword|prologue|introduction\s+by|about\s+(this|the)\s+book)\b", re.IGNORECASE),
    ),
    ("appendix", re.compile(r"^(appendix|appendices|annex(es)?|supplement(ary|s)?|attachment)\b", re.IGNORECASE)),
    (
        "references",
        re.compile(r"^(references|bibliography|works\s+cited|literature\s+cited|citations|further\s+reading|sources)\b", re.IGNORECASE),
    ),
    ("glossary", re.compile(r"^(glossary|nomenclature|definitions|abbreviations)\b", re.IGNORECASE)),
    ("notes", re.compile(r"^(notes|endnotes|footnotes)\b", re.IGNORECASE)),
    ("index", re.compile(r"^(index|subject\s+index|author\s+index)\b", re.IGNORECASE)),
    ("about", re.compile(r"^(about\s+the\s+authors?|biograph(y|ies)|contributors|colophon)\b", re.IGNORECASE)),
]

GROUPS: dict[SectionKind, SectionGroup] = {
    "cover": "front",
    "dedication": "front",
    "abstract": "front",
    "acknowledgements": "front",
    "contents": "front",
    "figures": "front",
    "preface": "front",
    "body": "body",
    "appendix": "back",
    "references": "back",
    "glossary": "back",
    "notes": "back",
    "index": "back",
    "about": "back",
}


def classify_section(title: str) -> SectionKind:
    trimmed = title.strip()
    for kind, pattern in PATTERNS:
        if pattern.search(trimmed):
            return kind
    return "body"


def group_of(kind: SectionKind) -> SectionGroup:
    return GROUPS[kind]
