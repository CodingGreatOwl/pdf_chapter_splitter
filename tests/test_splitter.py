from __future__ import annotations

import pytest

import pdf_chapter_splitter.splitter as splitter
from pdf_chapter_splitter.splitter import default_output_dir, to_chapters, to_equal_parts
from pdf_chapter_splitter.types import Bookmark, DetectedHeading, DetectedOutline, InvalidPdfError, NoOutlineError


@pytest.mark.case(
    id="UT-SPL-001",
    type="unit",
    requirement="REQ-SPL-EQUAL",
    goal="Return no chapters when total page count is invalid",
)
def test_to_equal_parts_returns_empty_for_non_positive_pages() -> None:
    assert to_equal_parts(0, 4) == []


@pytest.mark.case(
    id="UT-SPL-002",
    type="unit",
    requirement="REQ-SPL-EQUAL",
    goal="Distribute pages into near-equal sequential ranges",
)
def test_to_equal_parts_distributes_remainder_on_first_parts() -> None:
    chapters = to_equal_parts(10, 3)

    assert [chapter.title for chapter in chapters] == ["Part 01", "Part 02", "Part 03"]
    assert [(chapter.start_page, chapter.end_page) for chapter in chapters] == [(1, 4), (5, 7), (8, 10)]


@pytest.mark.case(
    id="UT-SPL-003",
    type="unit",
    requirement="REQ-SPL-EQUAL",
    goal="Clamp equal-part count to total page count when too large",
)
def test_to_equal_parts_caps_part_count_to_total_pages() -> None:
    chapters = to_equal_parts(3, 10)

    assert len(chapters) == 3
    assert [(chapter.start_page, chapter.end_page) for chapter in chapters] == [(1, 1), (2, 2), (3, 3)]


@pytest.mark.case(
    id="UT-SPL-004",
    type="unit",
    requirement="REQ-SPL-BOOKMARKS",
    goal="Return no chapters when bookmarks are missing",
)
def test_to_chapters_returns_empty_without_bookmarks() -> None:
    assert to_chapters([], 12) == []


@pytest.mark.case(
    id="UT-SPL-005",
    type="unit",
    requirement="REQ-SPL-BOOKMARKS",
    goal="Insert synthetic cover chapter before first bookmark page",
)
def test_to_chapters_inserts_cover_before_first_bookmark() -> None:
    chapters = to_chapters([Bookmark(title="Intro", page=3, level=1)], total_pages=8)

    assert chapters[0].title == "Cover"
    assert (chapters[0].start_page, chapters[0].end_page, chapters[0].kind, chapters[0].group) == (
        1,
        2,
        "cover",
        "front",
    )
    assert (chapters[1].title, chapters[1].start_page, chapters[1].end_page) == ("Intro", 3, 8)


@pytest.mark.case(
    id="UT-SPL-006",
    type="unit",
    requirement="REQ-SPL-BOOKMARKS",
    goal="Sort, clamp and classify bookmark-derived chapters",
)
def test_to_chapters_sorts_clamps_and_classifies() -> None:
    bookmarks = [
        Bookmark(title="References", page=99, level=1),
        Bookmark(title="Chapter 1", page=1, level=1),
        Bookmark(title="Appendix", page=-4, level=1),
    ]

    chapters = to_chapters(bookmarks, total_pages=20)

    assert [(chapter.title, chapter.start_page, chapter.end_page) for chapter in chapters] == [
        ("Appendix", 1, 1),
        ("Chapter 1", 1, 19),
        ("References", 20, 20),
    ]
    assert chapters[0].kind == "appendix"
    assert chapters[0].group == "back"
    assert chapters[-1].kind == "references"
    assert chapters[-1].group == "back"


@pytest.mark.case(
    id="UT-SPL-007",
    type="unit",
    requirement="REQ-SPL-BOOKMARKS",
    goal="Ensure duplicate chapter ids become unique with numeric suffixes",
)
def test_to_chapters_adds_suffix_for_duplicate_ids() -> None:
    bookmarks = [
        Bookmark(title="Intro", page=2, level=1),
        Bookmark(title="Intro", page=2, level=1),
    ]

    chapters = to_chapters(bookmarks, total_pages=6)
    intro_ids = [chapter.id for chapter in chapters if chapter.title == "Intro"]

    assert intro_ids == ["2-6-Intro", "2-6-Intro#1"]


@pytest.mark.case(
    id="UT-SPL-008",
    type="unit",
    requirement="REQ-SPL-OUTPUT",
    goal="Build default output folder next to source using sanitized stem",
)
def test_default_output_dir_uses_sanitized_stem() -> None:
    result = default_output_dir("/tmp/My:Draft?.pdf")
    assert result == "/tmp/My Draft"


@pytest.mark.case(
    id="UT-SPL-009",
    type="unit",
    requirement="REQ-SPL-PLAN",
    goal="Raise InvalidPdfError when the PDF reader fails to load",
)
def test_plan_sections_raises_invalid_pdf_when_reader_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_reader(_: str) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(splitter, "PdfReader", fake_reader)

    with pytest.raises(InvalidPdfError, match="Could not read PDF"):
        splitter.plan_sections("fake.pdf", mode="content")


@pytest.mark.case(
    id="UT-SPL-010",
    type="unit",
    requirement="REQ-SPL-PLAN",
    goal="Raise InvalidPdfError when PDF has zero pages",
)
def test_plan_sections_raises_invalid_pdf_for_empty_document(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeReader:
        pages: list[object] = []

    monkeypatch.setattr(splitter, "PdfReader", lambda _: FakeReader())

    with pytest.raises(InvalidPdfError, match="PDF has no pages"):
        splitter.plan_sections("fake.pdf", mode="content")


@pytest.mark.case(
    id="UT-SPL-011",
    type="unit",
    requirement="REQ-SPL-PLAN",
    goal="Use equal-parts planner directly in length mode",
)
def test_plan_sections_in_length_mode_returns_equal_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeReader:
        pages = [object()] * 9

    monkeypatch.setattr(splitter, "PdfReader", lambda _: FakeReader())

    chapters, total_pages, source = splitter.plan_sections("fake.pdf", mode="length", parts=4)

    assert source == "length"
    assert total_pages == 9
    assert [(chapter.start_page, chapter.end_page) for chapter in chapters] == [(1, 3), (4, 5), (6, 7), (8, 9)]


@pytest.mark.case(
    id="UT-SPL-012",
    type="unit",
    requirement="REQ-SPL-PLAN",
    goal="Prefer outline bookmarks over detected headings in content mode",
)
def test_plan_sections_prefers_outline_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeReader:
        pages = [object()] * 12

    bookmarks = [Bookmark(title="Chapter 1", page=2, level=1)]

    monkeypatch.setattr(splitter, "PdfReader", lambda _: FakeReader())
    monkeypatch.setattr(splitter, "read_outline", lambda _path, _depth: (bookmarks, 12))
    monkeypatch.setattr(splitter, "detect_outline", lambda _path: pytest.fail("detect_outline should not run"))

    chapters, total_pages, source = splitter.plan_sections("fake.pdf", mode="content", depth=1)

    assert source == "outline"
    assert total_pages == 12
    assert [chapter.title for chapter in chapters] == ["Cover", "Chapter 1"]


@pytest.mark.case(
    id="UT-SPL-013",
    type="unit",
    requirement="REQ-SPL-PLAN",
    goal="Use detected headings fallback when outline is missing",
)
def test_plan_sections_uses_detected_headings_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeReader:
        pages = [object()] * 10

    detected = DetectedOutline(
        headings=[
            DetectedHeading(title="Cover", page=1, level=1, kind="cover"),
            DetectedHeading(title="One", page=2, level=1, kind="body"),
            DetectedHeading(title="Two", page=6, level=1, kind="body"),
        ],
        confidence="medium",
        pages_scanned=10,
        text_per_page=120.0,
    )

    planned = [
        splitter._chapter("Cover", 1, 1, "cover"),
        splitter._chapter("One", 2, 5, "body"),
        splitter._chapter("Two", 6, 10, "body"),
    ]

    monkeypatch.setattr(splitter, "PdfReader", lambda _: FakeReader())
    monkeypatch.setattr(splitter, "read_outline", lambda _path, _depth: ([], 10))
    monkeypatch.setattr(splitter, "detect_outline", lambda _path: detected)
    monkeypatch.setattr(splitter, "plan_from_detected", lambda _d, _t, _depth: planned)

    chapters, total_pages, source = splitter.plan_sections("fake.pdf", mode="content", depth=2)

    assert source == "detected"
    assert total_pages == 10
    assert chapters == planned


@pytest.mark.case(
    id="UT-SPL-014",
    type="unit",
    requirement="REQ-SPL-PLAN",
    goal="Raise NoOutlineError when neither outline nor headings are available",
)
def test_plan_sections_raises_no_outline_error_without_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeReader:
        pages = [object()] * 10

    detected = DetectedOutline(headings=[], confidence="none", pages_scanned=10, text_per_page=0.0)

    monkeypatch.setattr(splitter, "PdfReader", lambda _: FakeReader())
    monkeypatch.setattr(splitter, "read_outline", lambda _path, _depth: ([], 10))
    monkeypatch.setattr(splitter, "detect_outline", lambda _path: detected)

    with pytest.raises(NoOutlineError, match="No outline and no detectable heading structure"):
        splitter.plan_sections("fake.pdf", mode="content")
