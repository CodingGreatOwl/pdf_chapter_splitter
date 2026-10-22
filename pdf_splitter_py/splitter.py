from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

from .detect import detect_outline, plan_from_detected, useful_depth
from .names import base_name_of, build_file_names, index_label
from .sections import classify_section, group_of
from .types import Bookmark, Chapter, InvalidPdfError, NoOutlineError, OutlineSummary, SectionKind

MAX_SUPPORTED_DEPTH = 12


def _chapter(title: str, start_page: int, end_page: int, kind: SectionKind) -> Chapter:
    return Chapter(
        id=f"{start_page}-{end_page}-{title}",
        title=title,
        start_page=start_page,
        end_page=end_page,
        kind=kind,
        group=group_of(kind),
    )


def _with_unique_ids(chapters: list[Chapter]) -> list[Chapter]:
    seen: dict[str, int] = defaultdict(int)
    for chapter in chapters:
        count = seen[chapter.id]
        seen[chapter.id] = count + 1
        if count > 0:
            chapter.id = f"{chapter.id}#{count}"
    return chapters


def to_chapters(bookmarks: list[Bookmark], total_pages: int) -> list[Chapter]:
    in_order = sorted(bookmarks, key=lambda b: b.page)
    if len(in_order) == 0 or total_pages < 1:
        return []

    chapters: list[Chapter] = []
    first_page = min(max(in_order[0].page, 1), total_pages)
    if first_page > 1:
        chapters.append(_chapter("Cover", 1, first_page - 1, "cover"))

    for index, bookmark in enumerate(in_order):
        next_bookmark = next((b for b in in_order[index + 1 :] if b.page > bookmark.page), None)
        start_page = min(max(bookmark.page, 1), total_pages)
        end_page = min((next_bookmark.page - 1) if next_bookmark else total_pages, total_pages)
        chapters.append(
            _chapter(
                bookmark.title,
                start_page,
                max(start_page, end_page),
                classify_section(bookmark.title),
            )
        )

    return _with_unique_ids(chapters)


def to_equal_parts(total_pages: int, parts: int) -> list[Chapter]:
    if total_pages < 1:
        return []

    count = max(1, min(int(parts), total_pages))
    base = total_pages // count
    remainder = total_pages % count

    chapters: list[Chapter] = []
    start = 1
    for index in range(count):
        size = base + (1 if index < remainder else 0)
        chapters.append(
            _chapter(f"Part {index_label(index + 1, count)}", start, start + size - 1, "body")
        )
        start += size
    return chapters


def _is_outline_item(item: Any) -> bool:
    return hasattr(item, "title")


def read_outline(path: str, max_depth: int) -> tuple[list[Bookmark], int]:
    try:
        reader = PdfReader(path)
    except Exception as error:  # pragma: no cover
        raise InvalidPdfError("Could not read PDF") from error

    total_pages = len(reader.pages)

    def walk(items: list[Any], level: int, out: list[Bookmark]) -> None:
        if level > max_depth:
            return
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1, out)
                continue
            if not _is_outline_item(item):
                continue
            title = str(getattr(item, "title", "Untitled") or "Untitled").strip() or "Untitled"
            try:
                page = int(reader.get_destination_page_number(item)) + 1
            except Exception:
                continue
            out.append(Bookmark(title=title, page=page, level=level))

    items = reader.outline if hasattr(reader, "outline") else []
    out: list[Bookmark] = []
    if isinstance(items, list):
        walk(items, 1, out)
    return out, total_pages


def inspect_outline(path: str) -> OutlineSummary:
    bookmarks, total_pages = read_outline(path, MAX_SUPPORTED_DEPTH)
    if len(bookmarks) == 0:
        raise NoOutlineError("No table of contents in this PDF")

    max_depth = max([1] + [bookmark.level for bookmark in bookmarks])
    chapters_at_depth = [
        len(to_chapters([bookmark for bookmark in bookmarks if bookmark.level <= depth], total_pages))
        for depth in range(1, max_depth + 1)
    ]
    return OutlineSummary(max_depth=max_depth, chapters_at_depth=chapters_at_depth, total_pages=total_pages)


def plan_sections(path: str, mode: str, depth: int = 1, parts: int = 4) -> tuple[list[Chapter], int, str]:
    try:
        reader = PdfReader(path)
        total_pages = len(reader.pages)
    except Exception as error:  # pragma: no cover
        raise InvalidPdfError("Could not read PDF") from error

    if total_pages < 1:
        raise InvalidPdfError("PDF has no pages")

    if mode == "length":
        return to_equal_parts(total_pages, parts), total_pages, "length"

    bookmarks, _ = read_outline(path, max(1, depth))
    if len(bookmarks) > 0:
        return to_chapters(bookmarks, total_pages), total_pages, "outline"

    detected = detect_outline(path)
    if len(detected.headings) >= 2:
        actual_depth = useful_depth(detected, total_pages) if depth <= 0 else depth
        return plan_from_detected(detected, total_pages, actual_depth), total_pages, "detected"

    raise NoOutlineError(
        "No outline and no detectable heading structure. Use --mode length to split equally."
    )


def extract(path: str, source_name: str, chapters: list[Chapter], numbered: bool, output_dir: str) -> list[Path]:
    reader = PdfReader(path)
    total_pages = len(reader.pages)
    file_names = build_file_names(
        source_name,
        [{"title": chapter.title, "numbered": numbered} for chapter in chapters],
    )

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, chapter in enumerate(chapters):
        start = max(1, min(chapter.start_page, total_pages))
        end = max(start, min(chapter.end_page, total_pages))
        writer = PdfWriter()
        for page in range(start - 1, end):
            writer.add_page(reader.pages[page])

        out_path = target_dir / file_names[index]
        with out_path.open("wb") as handle:
            writer.write(handle)
        written.append(out_path)

    return written


def default_output_dir(input_path: str) -> str:
    source = Path(input_path)
    return str(source.parent / base_name_of(source.name))
