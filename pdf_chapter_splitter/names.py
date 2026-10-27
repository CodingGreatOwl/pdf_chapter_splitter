from __future__ import annotations

import re

MAX_TITLE_LENGTH = 60

WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$", re.IGNORECASE)
RESERVED_PUNCTUATION = re.compile(r"[<>:\"/\\|?*]")


def index_label(value: int, total: int) -> str:
    """Return a zero-padded index string sized for the total part count."""
    width = max(2, len(str(max(total, 1))))
    return str(value).rjust(width, "0")


def strip_control_characters(value: str) -> str:
    """Remove ASCII control characters so file labels stay portable."""
    out: list[str] = []
    for ch in value:
        code = ord(ch)
        if code >= 32 and code != 127:
            out.append(ch)
    return "".join(out)


def sanitize_title(title: str) -> str:
    """Normalize a title into a safe filename segment for cross-platform use."""
    cleaned = strip_control_characters(title)
    cleaned = RESERVED_PUNCTUATION.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^[.\-\s]+", "", cleaned)
    cleaned = re.sub(r"[.\-\s]+$", "", cleaned)
    cleaned = cleaned[:MAX_TITLE_LENGTH].strip()

    if not cleaned:
        return "Untitled"
    if WINDOWS_RESERVED.match(cleaned):
        return f"_{cleaned}"
    return cleaned


def base_name_of(file_name: str) -> str:
    """Return a sanitized document stem without the trailing .pdf extension."""
    stem = re.sub(r"\.pdf$", "", file_name, flags=re.IGNORECASE)
    return sanitize_title(stem) or "Document"


def build_file_names(source: str, parts: list[dict[str, object]]) -> list[str]:
    """Build unique output filenames for split parts from source and part metadata."""
    stem = base_name_of(source)
    taken: set[str] = set()
    names: list[str] = []

    for index, part in enumerate(parts, start=1):
        numeral = index_label(index, len(parts))
        numbered = bool(part.get("numbered"))
        title = str(part.get("title") or "")
        label = f"Part {numeral}" if numbered else f"{numeral} - {sanitize_title(title)}"
        base = f"{stem} - {label}"
        name = f"{base}.pdf"
        suffix = 2
        while name.lower() in taken:
            name = f"{base} ({suffix}).pdf"
            suffix += 1
        taken.add(name.lower())
        names.append(name)

    return names
