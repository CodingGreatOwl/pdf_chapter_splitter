from __future__ import annotations

import re

MAX_TITLE_LENGTH = 60

WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$", re.IGNORECASE)
RESERVED_PUNCTUATION = re.compile(r"[<>:\"/\\|?*]")


def index_label(value: int, total: int) -> str:
    width = max(2, len(str(max(total, 1))))
    return str(value).rjust(width, "0")


def strip_control_characters(value: str) -> str:
    out: list[str] = []
    for ch in value:
        code = ord(ch)
        if code >= 32 and code != 127:
            out.append(ch)
    return "".join(out)


def sanitize_title(title: str) -> str:
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
    stem = re.sub(r"\.pdf$", "", file_name, flags=re.IGNORECASE)
    return sanitize_title(stem) or "Document"


def build_file_names(source: str, parts: list[dict[str, object]]) -> list[str]:
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
