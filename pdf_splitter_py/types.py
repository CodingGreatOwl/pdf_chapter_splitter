from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SectionGroup = Literal["front", "body", "back"]
SectionKind = Literal[
    "cover",
    "dedication",
    "abstract",
    "acknowledgements",
    "contents",
    "figures",
    "preface",
    "body",
    "appendix",
    "references",
    "glossary",
    "notes",
    "index",
    "about",
]


@dataclass(slots=True)
class Bookmark:
    title: str
    page: int
    level: int


@dataclass(slots=True)
class Chapter:
    id: str
    title: str
    group: SectionGroup
    kind: SectionKind
    start_page: int
    end_page: int

    @property
    def page_count(self) -> int:
        return self.end_page - self.start_page + 1


@dataclass(slots=True)
class OutlineSummary:
    max_depth: int
    chapters_at_depth: list[int]
    total_pages: int


@dataclass(slots=True)
class Line:
    text: str
    size: float
    from_top: float
    page: int
    centred: bool


@dataclass(slots=True)
class DetectedHeading:
    title: str
    page: int
    level: int
    kind: SectionKind


@dataclass(slots=True)
class DetectedOutline:
    headings: list[DetectedHeading]
    confidence: Literal["none", "low", "medium", "high"]
    pages_scanned: int
    text_per_page: float


class NoOutlineError(Exception):
    pass


class InvalidPdfError(Exception):
    pass
