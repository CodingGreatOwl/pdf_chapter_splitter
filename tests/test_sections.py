from __future__ import annotations

import pytest

from pdf_chapter_splitter.sections import classify_section, group_of


@pytest.mark.case(
    id="UT-SEC-001",
    type="unit",
    requirement="REQ-SEC-CLASSIFY",
    goal="Classify front-matter titles with canonical keywords",
)
@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Cover", "cover"),
        ("Dedication", "dedication"),
        ("Executive Summary", "abstract"),
        ("Acknowledgements", "acknowledgements"),
        ("Table of Contents", "contents"),
        ("List of Figures", "figures"),
        ("Preface", "preface"),
    ],
)
def test_classify_section_front_matter_titles(title: str, expected: str) -> None:
    assert classify_section(title) == expected


@pytest.mark.case(
    id="UT-SEC-002",
    type="unit",
    requirement="REQ-SEC-CLASSIFY",
    goal="Classify back-matter titles with canonical keywords",
)
@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Appendix", "appendix"),
        ("References", "references"),
        ("Glossary", "glossary"),
        ("Notes", "notes"),
        ("Index", "index"),
        ("About the Author", "about"),
    ],
)
def test_classify_section_back_matter_titles(title: str, expected: str) -> None:
    assert classify_section(title) == expected


@pytest.mark.case(
    id="UT-SEC-003",
    type="unit",
    requirement="REQ-SEC-CLASSIFY",
    goal="Return body when title does not match known patterns",
)
def test_classify_section_returns_body_for_unknown_titles() -> None:
    assert classify_section("Chapter 7 - Advanced Topics") == "body"


@pytest.mark.case(
    id="UT-SEC-004",
    type="unit",
    requirement="REQ-SEC-CLASSIFY",
    goal="Ignore surrounding whitespace while matching section titles",
)
def test_classify_section_ignores_surrounding_whitespace() -> None:
    assert classify_section("   bibliography   ") == "references"


@pytest.mark.case(
    id="UT-SEC-005",
    type="unit",
    requirement="REQ-SEC-GROUP",
    goal="Map each section kind to expected high-level group",
)
@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("cover", "front"),
        ("dedication", "front"),
        ("abstract", "front"),
        ("acknowledgements", "front"),
        ("contents", "front"),
        ("figures", "front"),
        ("preface", "front"),
        ("body", "body"),
        ("appendix", "back"),
        ("references", "back"),
        ("glossary", "back"),
        ("notes", "back"),
        ("index", "back"),
        ("about", "back"),
    ],
)
def test_group_of_maps_section_kinds(kind: str, expected: str) -> None:
    assert group_of(kind) == expected
