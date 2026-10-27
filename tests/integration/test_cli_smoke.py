from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MATERIAL = ROOT / "tests" / "testingMaterial"


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pdf_chapter_splitter.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.integration
@pytest.mark.case(
    id="IT-CLI-001",
    type="integration",
    requirement="REQ-INT-BOOKMARK",
    goal="Split bookmarked PDF in content mode and write output files",
)
def test_cli_splits_bookmarked_pdf_content_mode(tmp_path: Path) -> None:
    output_dir = tmp_path / "bookmarked"
    result = _run_cli(
        [
            str(MATERIAL / "DocWithBookmark.pdf"),
            "--mode",
            "content",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result.returncode == 0, result.stderr
    assert "PDF Splitter - Conversion Summary" in result.stdout
    generated = sorted(output_dir.glob("*.pdf"))
    assert len(generated) >= 1


@pytest.mark.integration
@pytest.mark.case(
    id="IT-CLI-002",
    type="integration",
    requirement="REQ-INT-NO-BOOKMARK",
    goal="Split PDF without bookmarks using length mode",
)
def test_cli_splits_pdf_without_bookmarks_in_length_mode(tmp_path: Path) -> None:
    output_dir = tmp_path / "without-bookmark"
    result = _run_cli(
        [
            str(MATERIAL / "DocWithoutBookmark.pdf"),
            "--mode",
            "length",
            "--parts",
            "3",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result.returncode == 0, result.stderr
    assert "Split mode" in result.stdout
    assert "length" in result.stdout
    generated = sorted(output_dir.glob("*.pdf"))
    assert len(generated) == 3


@pytest.mark.integration
@pytest.mark.case(
    id="IT-CLI-003",
    type="integration",
    requirement="REQ-INT-MISSING",
    goal="Return domain error for missing input PDF",
)
def test_cli_returns_error_for_missing_file(tmp_path: Path) -> None:
    result = _run_cli(
        [
            str(MATERIAL / "DoesNotExist.pdf"),
            "--output-dir",
            str(tmp_path / "missing"),
        ]
    )

    assert result.returncode == 2
    assert "error: Could not read PDF" in result.stderr


@pytest.mark.integration
@pytest.mark.case(
    id="IT-CLI-004",
    type="integration",
    requirement="REQ-INT-CORRUPTED",
    goal="Return domain error for corrupted PDF input",
)
def test_cli_returns_error_for_corrupted_file(tmp_path: Path) -> None:
    result = _run_cli(
        [
            str(MATERIAL / "CorruptedFile.pdf"),
            "--output-dir",
            str(tmp_path / "corrupted"),
        ]
    )

    assert result.returncode == 2
    assert "error: Could not read PDF" in result.stderr
