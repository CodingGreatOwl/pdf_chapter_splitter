from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Literal

import pdfplumber

from .sections import classify_section, group_of
from .types import Chapter, DetectedHeading, DetectedOutline, Line, SectionKind

SIZE_TOLERANCE = 1.06
HEADING_RATIO = 1.15
MIN_PER_TIER = 2
MAX_PER_TIER = 60
MAX_HEADING_CHARS = 90
MAX_TIERS = 3


def _char_geometry(char: dict[str, Any]) -> tuple[float, float, float]:
    """Return the top, left, and right coordinates of a character."""
    top = float(char.get("top") or 0)
    x0 = float(char.get("x0") or 0)
    x1 = float(char.get("x1") or x0)
    return top, x0, x1


def _add_char(rows: dict[int, dict[str, float | str]], char: dict[str, Any]) -> None:
    """Merge a character into its rounded text row."""
    text = str(char.get("text") or "")
    if not text.strip():
        return

    size = float(char.get("size") or 0)
    if size <= 0:
        return

    top, x0, x1 = _char_geometry(char)
    key = int(round(top / 2) * 2)
    row = rows.get(key)

    if row is None:
        rows[key] = {
            "text": text,
            "size": size,
            "x": x0,
            "right": x1,
        }
        return

    row["text"] = f"{row['text']}{text}"
    row["size"] = max(float(row["size"]), size)
    row["right"] = max(float(row["right"]), x1)


def _page_lines(
    rows: dict[int, dict[str, float | str]], width: float, page_number: int
) -> list[Line]:
    """Convert character rows from one page into normalized text lines."""
    lines: list[Line] = []
    for top, row in rows.items():
        text = " ".join(str(row["text"]).split()).strip()
        if not text:
            continue

        middle = (float(row["x"]) + float(row["right"])) / 2
        centred = abs(middle - width / 2) < width * 0.12 if width > 0 else False
        lines.append(
            Line(
                text=text,
                size=float(row["size"]),
                from_top=float(top),
                page=page_number,
                centred=centred,
            )
        )
    return lines


def read_lines(path: str) -> tuple[list[Line], int]:
    """Read a PDF's text layout and return its lines and page count."""
    lines: list[Line] = []
    pages_read = 0

    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            width = float(page.width or 0)
            rows: dict[int, dict[str, float | str]] = {}

            for char in page.chars:
                _add_char(rows, char)

            lines.extend(_page_lines(rows, width, page_number))
            pages_read = page_number

    return lines, pages_read


def body_size(lines: list[Line]) -> float:
    """Return the most common character-weighted font size in the document."""
    weight: dict[float, int] = defaultdict(int)
    for line in lines:
        key = round(line.size * 2) / 2
        weight[key] += len(line.text)

    best = 0.0
    most = -1
    for size, chars in weight.items():
        if chars > most:
            most = chars
            best = size
    return best


def to_tiers(sizes: list[float]) -> list[list[float]]:
    """Group font sizes into descending tiers within the size tolerance."""
    sorted_sizes = sorted(set(sizes), reverse=True)
    tiers: list[list[float]] = []

    for size in sorted_sizes:
        if tiers and tiers[-1][0] / size <= SIZE_TOLERANCE:
            tiers[-1].append(size)
        else:
            tiers.append([size])

    return tiers


def looks_like_cover(lines: list[Line], body: float) -> bool:
    """Return True when page one resembles a sparse, large-type cover."""
    on_page_one = [line for line in lines if line.page == 1]
    if len(on_page_one) == 0 or len(on_page_one) > 12:
        return False

    characters = sum(len(line.text) for line in on_page_one)
    if characters > 300:
        return False

    largest = max(line.size for line in on_page_one)
    if largest < body * 1.4:
        return False

    return len([line for line in on_page_one if line.size <= body * 1.05]) <= 3


def characters_per_page(lines: list[Line], pages: int) -> float:
    """Return the average number of characters per page."""
    if len(lines) == 0 or pages < 1:
        return 0.0
    return sum(len(line.text) for line in lines) / pages


def _is_candidate(line: Line, body: float) -> bool:
    """Return True when a line is large enough and short enough to be a heading."""
    return (
        line.size >= body * HEADING_RATIO
        and len(line.text) <= MAX_HEADING_CHARS
        and not bool(re.search(r"[.;]\s+\S", line.text))
    )


def _select_candidates(lines: list[Line], body: float) -> list[Line]:
    """Return the lines eligible to become headings."""
    return [line for line in lines if _is_candidate(line, body)]


def _tier_is_usable(tier: list[Line]) -> bool:
    """Return True when a size tier has enough near-top heading lines."""
    if len(tier) < MIN_PER_TIER or len(tier) > MAX_PER_TIER:
        return False
    top_aligned = len([line for line in tier if line.from_top < 300])
    return top_aligned / len(tier) >= 0.5


def _accepted_tiers(candidates: list[Line]) -> list[list[Line]]:
    """Return usable candidate tiers, capped at the maximum tier count."""
    accepted: list[list[Line]] = []
    for tier in to_tiers([line.size for line in candidates]):
        in_tier = [line for line in candidates if line.size in tier]
        if not _tier_is_usable(in_tier):
            continue
        accepted.append(in_tier)
        if len(accepted) == MAX_TIERS:
            break
    return accepted


def _headings_from_tiers(accepted: list[list[Line]], cover: bool) -> list[DetectedHeading]:
    """Build headings from accepted tiers, optionally adding a cover heading."""
    headings: list[DetectedHeading] = []
    if cover:
        headings.append(DetectedHeading(title="Cover", page=1, level=1, kind="cover"))

    for index, tier in enumerate(accepted, start=1):
        for line in tier:
            if cover and line.page == 1:
                continue
            headings.append(
                DetectedHeading(
                    title=line.text,
                    page=line.page,
                    level=index,
                    kind=classify_section(line.text),
                )
            )
    return headings


def _unique_headings(headings: list[DetectedHeading]) -> list[DetectedHeading]:
    """Sort headings by page and level, keeping the first one per page."""
    headings.sort(key=lambda h: (h.page, h.level))
    unique: list[DetectedHeading] = []
    for heading in headings:
        if not unique or heading.page != unique[-1].page:
            unique.append(heading)
    return unique


def _confidence(
    accepted: list[list[Line]], cover: bool, unique: list[DetectedHeading]
) -> Literal["low", "medium", "high"]:
    """Score detection confidence from tiers, cover, and page coverage."""
    starts_page = len([heading for heading in unique if heading.page > 1])
    signals = int(len(accepted) > 1) + int(cover) + int(starts_page >= len(unique) * 0.8)
    if len(unique) < 2:
        return "low"
    return "high" if signals >= 2 else "medium"


def detect_from_lines(lines: list[Line], pages_scanned: int | None = None) -> DetectedOutline:
    """Detect outline headings from pre-extracted text lines."""
    total_pages = pages_scanned or (max((line.page for line in lines), default=0))
    empty = DetectedOutline(
        headings=[],
        confidence="none",
        pages_scanned=total_pages,
        text_per_page=characters_per_page(lines, total_pages),
    )

    if len(lines) == 0:
        return empty

    body = body_size(lines)
    if body <= 0:
        return empty

    candidates = _select_candidates(lines, body)
    cover = looks_like_cover(lines, body)
    accepted = _accepted_tiers(candidates)
    if len(accepted) == 0:
        return empty

    unique = _unique_headings(_headings_from_tiers(accepted, cover))
    return DetectedOutline(
        headings=unique,
        confidence=_confidence(accepted, cover, unique),
        pages_scanned=total_pages,
        text_per_page=empty.text_per_page,
    )


def detect_outline(path: str) -> DetectedOutline:
    """Detect outline headings by reading a PDF's text layout."""
    lines, pages = read_lines(path)
    return detect_from_lines(lines, pages)


def _chapter(title: str, start_page: int, end_page: int, kind: SectionKind) -> Chapter:
    """Build a chapter record with derived id and section group."""
    return Chapter(
        id=f"{start_page}-{end_page}-{title}",
        title=title,
        start_page=start_page,
        end_page=end_page,
        kind=kind,
        group=group_of(kind),
    )


def _with_unique_ids(chapters: list[Chapter]) -> list[Chapter]:
    """Ensure repeated chapter ids receive a stable numeric suffix."""
    seen: dict[str, int] = defaultdict(int)
    for chapter in chapters:
        count = seen[chapter.id]
        seen[chapter.id] = count + 1
        if count > 0:
            chapter.id = f"{chapter.id}#{count}"
    return chapters


def detected_to_chapters(detected: DetectedOutline, total_pages: int, max_level: int = 1) -> list[Chapter]:
    """Convert detected headings to non-overlapping chapter page ranges."""
    marks = sorted(
        [heading for heading in detected.headings if heading.level <= max_level],
        key=lambda h: h.page,
    )
    if len(marks) == 0 or total_pages < 1:
        return []

    chapters: list[Chapter] = []
    first_page = min(max(marks[0].page, 1), total_pages)
    if first_page > 1:
        chapters.append(_chapter("Cover", 1, first_page - 1, "cover"))

    for index, mark in enumerate(marks):
        next_mark = next((m for m in marks[index + 1 :] if m.page > mark.page), None)
        start = min(max(mark.page, 1), total_pages)
        end = min((next_mark.page - 1) if next_mark else total_pages, total_pages)
        chapters.append(_chapter(mark.title, start, max(start, end), mark.kind))

    return _with_unique_ids(chapters)


def detected_depths(detected: DetectedOutline, total_pages: int) -> list[int]:
    """Return chapter counts for each heading depth from shallowest to deepest."""
    deepest = max([1] + [heading.level for heading in detected.headings])
    return [len(detected_to_chapters(detected, total_pages, level)) for level in range(1, deepest + 1)]


def useful_depth(detected: DetectedOutline, total_pages: int) -> int:
    """Return the shallowest depth that produces at least three chapters."""
    counts = detected_depths(detected, total_pages)
    for index, count in enumerate(counts, start=1):
        if count >= 3:
            return index
    return max(len(counts), 1)


def plan_from_detected(detected: DetectedOutline, total_pages: int, depth: int) -> list[Chapter]:
    """Plan chapters from detected headings at the requested depth."""
    return detected_to_chapters(detected, total_pages, depth)
