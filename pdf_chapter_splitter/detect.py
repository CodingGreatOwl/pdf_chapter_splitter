from __future__ import annotations

from collections import defaultdict
import re

import pdfplumber

from .sections import classify_section, group_of
from .types import Chapter, DetectedHeading, DetectedOutline, Line, SectionKind

SIZE_TOLERANCE = 1.06
HEADING_RATIO = 1.15
MIN_PER_TIER = 2
MAX_PER_TIER = 60
MAX_HEADING_CHARS = 90
MAX_TIERS = 3


def read_lines(path: str) -> tuple[list[Line], int]:
    lines: list[Line] = []
    pages_read = 0

    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            width = float(page.width or 0)
            rows: dict[int, dict[str, float | str]] = {}

            for char in page.chars:
                text = str(char.get("text") or "")
                if not text.strip():
                    continue

                size = float(char.get("size") or 0)
                if size <= 0:
                    continue

                top = float(char.get("top") or 0)
                x0 = float(char.get("x0") or 0)
                x1 = float(char.get("x1") or x0)
                key = int(round(top / 2) * 2)
                row = rows.get(key)

                if row is None:
                    rows[key] = {
                        "text": text,
                        "size": size,
                        "x": x0,
                        "right": x1,
                    }
                else:
                    row["text"] = f"{row['text']}{text}"
                    row["size"] = max(float(row["size"]), size)
                    row["right"] = max(float(row["right"]), x1)

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

            pages_read = page_number

    return lines, pages_read


def body_size(lines: list[Line]) -> float:
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
    sorted_sizes = sorted(set(sizes), reverse=True)
    tiers: list[list[float]] = []

    for size in sorted_sizes:
        if tiers and tiers[-1][0] / size <= SIZE_TOLERANCE:
            tiers[-1].append(size)
        else:
            tiers.append([size])

    return tiers


def looks_like_cover(lines: list[Line], body: float) -> bool:
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
    if len(lines) == 0 or pages < 1:
        return 0.0
    return sum(len(line.text) for line in lines) / pages


def detect_from_lines(lines: list[Line], pages_scanned: int | None = None) -> DetectedOutline:
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

    candidates = [
        line
        for line in lines
        if line.size >= body * HEADING_RATIO
        and len(line.text) <= MAX_HEADING_CHARS
        and not bool(re.search(r"[.;]\s+\S", line.text))
    ]

    cover = looks_like_cover(lines, body)
    accepted: list[list[Line]] = []

    for tier in to_tiers([line.size for line in candidates]):
        in_tier = [line for line in candidates if line.size in tier]
        if len(in_tier) < MIN_PER_TIER or len(in_tier) > MAX_PER_TIER:
            continue
        if (len([line for line in in_tier if line.from_top < 300]) / len(in_tier)) < 0.5:
            continue
        accepted.append(in_tier)
        if len(accepted) == MAX_TIERS:
            break

    if len(accepted) == 0:
        return empty

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

    headings.sort(key=lambda h: (h.page, h.level))
    unique: list[DetectedHeading] = []
    for heading in headings:
        if not unique or heading.page != unique[-1].page:
            unique.append(heading)

    starts_page = len([h for h in unique if h.page > 1])
    signals = (1 if len(accepted) > 1 else 0) + (1 if cover else 0) + (
        1 if starts_page >= len(unique) * 0.8 else 0
    )

    confidence = "low" if len(unique) < 2 else ("high" if signals >= 2 else "medium")
    return DetectedOutline(
        headings=unique,
        confidence=confidence,
        pages_scanned=total_pages,
        text_per_page=empty.text_per_page,
    )


def detect_outline(path: str) -> DetectedOutline:
    lines, pages = read_lines(path)
    return detect_from_lines(lines, pages)


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


def detected_to_chapters(detected: DetectedOutline, total_pages: int, max_level: int = 1) -> list[Chapter]:
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
    deepest = max([1] + [heading.level for heading in detected.headings])
    return [len(detected_to_chapters(detected, total_pages, level)) for level in range(1, deepest + 1)]


def useful_depth(detected: DetectedOutline, total_pages: int) -> int:
    counts = detected_depths(detected, total_pages)
    for index, count in enumerate(counts, start=1):
        if count >= 3:
            return index
    return max(len(counts), 1)


def plan_from_detected(detected: DetectedOutline, total_pages: int, depth: int) -> list[Chapter]:
    return detected_to_chapters(detected, total_pages, depth)
