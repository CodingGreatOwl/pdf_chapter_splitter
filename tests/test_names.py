from __future__ import annotations

import pytest

from pdf_splitter_py.names import (
    MAX_TITLE_LENGTH,
    base_name_of,
    build_file_names,
    index_label,
    sanitize_title,
    strip_control_characters,
)


@pytest.mark.case(
    id="UT-NAME-001",
    type="unit",
    requirement="REQ-NAME-INDEX",
    goal="Pad index labels to at least two digits",
)
def test_index_label_uses_minimum_two_digits() -> None:
    assert index_label(1, 4) == "01"


@pytest.mark.case(
    id="UT-NAME-002",
    type="unit",
    requirement="REQ-NAME-INDEX",
    goal="Pad index labels to total width for larger part counts",
)
def test_index_label_scales_with_total_width() -> None:
    assert index_label(9, 1200) == "0009"


@pytest.mark.case(
    id="UT-NAME-003",
    type="unit",
    requirement="REQ-NAME-SANITIZE",
    goal="Drop ASCII control characters from title text",
)
def test_strip_control_characters_removes_ascii_controls() -> None:
    assert strip_control_characters("A\x00B\x1fC\x7fD") == "ABCD"


@pytest.mark.case(
    id="UT-NAME-004",
    type="unit",
    requirement="REQ-NAME-SANITIZE",
    goal="Replace reserved punctuation and normalize whitespace",
)
def test_sanitize_title_replaces_reserved_characters() -> None:
    assert sanitize_title(' Intro:/\\*?"<>|   section ') == "Intro section"


@pytest.mark.case(
    id="UT-NAME-005",
    type="unit",
    requirement="REQ-NAME-SANITIZE",
    goal="Trim leading and trailing dots, dashes, and spaces",
)
def test_sanitize_title_trims_surrounding_punctuation() -> None:
    assert sanitize_title(" ..- Chapter 1 -.. ") == "Chapter 1"


@pytest.mark.case(
    id="UT-NAME-006",
    type="unit",
    requirement="REQ-NAME-SANITIZE",
    goal="Return Untitled when sanitization removes all content",
)
def test_sanitize_title_falls_back_to_untitled() -> None:
    assert sanitize_title("\x00\x1f  --..  ") == "Untitled"


@pytest.mark.case(
    id="UT-NAME-007",
    type="unit",
    requirement="REQ-NAME-SANITIZE",
    goal="Prefix Windows reserved names to keep them valid",
)
def test_sanitize_title_prefixes_windows_reserved_words() -> None:
    assert sanitize_title("CON") == "_CON"


@pytest.mark.case(
    id="UT-NAME-008",
    type="unit",
    requirement="REQ-NAME-SANITIZE",
    goal="Clamp sanitized title length to MAX_TITLE_LENGTH",
)
def test_sanitize_title_limits_length() -> None:
    cleaned = sanitize_title("A" * (MAX_TITLE_LENGTH + 25))
    assert len(cleaned) == MAX_TITLE_LENGTH


@pytest.mark.case(
    id="UT-NAME-009",
    type="unit",
    requirement="REQ-NAME-BASENAME",
    goal="Remove PDF extension case-insensitively from source names",
)
def test_base_name_of_removes_pdf_extension_case_insensitively() -> None:
    assert base_name_of("Guide.PDF") == "Guide"


@pytest.mark.case(
    id="UT-NAME-010",
    type="unit",
    requirement="REQ-NAME-BUILD",
    goal="Build non-numbered names with sequence and sanitized title",
)
def test_build_file_names_non_numbered_mode() -> None:
    names = build_file_names(
        "Manual.pdf",
        [
            {"title": "Intro", "numbered": False},
            {"title": "Setup", "numbered": False},
        ],
    )
    assert names == [
        "Manual - 01 - Intro.pdf",
        "Manual - 02 - Setup.pdf",
    ]


@pytest.mark.case(
    id="UT-NAME-011",
    type="unit",
    requirement="REQ-NAME-BUILD",
    goal="Build numbered names as Part labels for equal-split output",
)
def test_build_file_names_numbered_mode_uses_part_label() -> None:
    names = build_file_names(
        "Manual.pdf",
        [
            {"title": "ignored", "numbered": True},
            {"title": "ignored", "numbered": True},
        ],
    )
    assert names == [
        "Manual - Part 01.pdf",
        "Manual - Part 02.pdf",
    ]


@pytest.mark.case(
    id="UT-NAME-012",
    type="unit",
    requirement="REQ-NAME-BUILD",
    goal="Sanitize source stem before composing output names",
)
def test_build_file_names_sanitizes_source_stem() -> None:
    names = build_file_names(
        "Manual:Draft?.pdf",
        [
            {"title": "Chapter 1", "numbered": False},
        ],
    )
    assert names == ["Manual Draft - 01 - Chapter 1.pdf"]
