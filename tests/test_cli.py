from __future__ import annotations

from pathlib import Path

import pytest

import pdf_splitter_py.cli as cli
from pdf_splitter_py.types import InvalidPdfError, NoOutlineError


@pytest.mark.case(
    id="UT-CLI-001",
    type="unit",
    requirement="REQ-CLI-PARSER",
    goal="Use expected default parser values when optional flags are omitted",
)
def test_build_parser_uses_expected_defaults() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["book.pdf"])

    assert args.input == "book.pdf"
    assert args.mode == "content"
    assert args.depth == 1
    assert args.parts == 4
    assert args.output_dir is None


@pytest.mark.case(
    id="UT-CLI-002",
    type="unit",
    requirement="REQ-CLI-PARSER",
    goal="Parse explicit mode, depth, parts, and output options",
)
def test_build_parser_parses_explicit_flags() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        ["book.pdf", "--mode", "length", "--depth", "3", "--parts", "7", "--output-dir", "outdir"]
    )

    assert args.mode == "length"
    assert args.depth == 3
    assert args.parts == 7
    assert args.output_dir == "outdir"


@pytest.mark.case(
    id="UT-CLI-003",
    type="unit",
    requirement="REQ-CLI-MAIN",
    goal="Use computed default output dir and normalized depth/parts in content mode",
)
def test_main_uses_default_output_and_normalized_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    def fake_default_output_dir(input_path: str) -> str:
        captured["default_output_input"] = input_path
        return "derived-out"

    def fake_plan_sections(path: str, mode: str, depth: int, parts: int):
        captured["plan"] = {
            "path": path,
            "mode": mode,
            "depth": depth,
            "parts": parts,
        }
        return ([object()], 8, "outline")

    def fake_extract(path: str, source_name: str, chapters: list[object], numbered: bool, output_dir: str):
        captured["extract"] = {
            "path": path,
            "source_name": source_name,
            "chapters_count": len(chapters),
            "numbered": numbered,
            "output_dir": output_dir,
        }
        return [Path("a.pdf")]

    monkeypatch.setattr(cli, "default_output_dir", fake_default_output_dir)
    monkeypatch.setattr(cli, "plan_sections", fake_plan_sections)
    monkeypatch.setattr(cli, "extract", fake_extract)

    exit_code = cli.main(["docs/book.pdf", "--depth", "0", "--parts", "0"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured["default_output_input"] == "docs/book.pdf"
    assert captured["plan"] == {
        "path": "docs/book.pdf",
        "mode": "content",
        "depth": 1,
        "parts": 1,
    }
    assert captured["extract"] == {
        "path": "docs/book.pdf",
        "source_name": "book.pdf",
        "chapters_count": 1,
        "numbered": False,
        "output_dir": "derived-out",
    }
    assert "Split mode" in stdout
    assert "content" in stdout
    assert "Structure source" in stdout


@pytest.mark.case(
    id="UT-CLI-004",
    type="unit",
    requirement="REQ-CLI-MAIN",
    goal="Pass length mode settings and mark extraction as numbered",
)
def test_main_in_length_mode_marks_numbered_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    def fake_plan_sections(path: str, mode: str, depth: int, parts: int):
        captured["plan"] = {
            "path": path,
            "mode": mode,
            "depth": depth,
            "parts": parts,
        }
        return ([object(), object()], 12, "length")

    def fake_extract(path: str, source_name: str, chapters: list[object], numbered: bool, output_dir: str):
        captured["extract"] = {
            "source_name": source_name,
            "numbered": numbered,
            "output_dir": output_dir,
            "chapters_count": len(chapters),
        }
        return [Path("p1.pdf"), Path("p2.pdf")]

    monkeypatch.setattr(cli, "plan_sections", fake_plan_sections)
    monkeypatch.setattr(cli, "extract", fake_extract)

    exit_code = cli.main(["book.pdf", "--mode", "length", "--parts", "5", "--output-dir", "my-out"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured["plan"] == {
        "path": "book.pdf",
        "mode": "length",
        "depth": 1,
        "parts": 5,
    }
    assert captured["extract"] == {
        "source_name": "book.pdf",
        "numbered": True,
        "output_dir": "my-out",
        "chapters_count": 2,
    }
    assert "Parts" in stdout
    assert "5" in stdout


@pytest.mark.case(
    id="UT-CLI-005",
    type="unit",
    requirement="REQ-CLI-ERRORS",
    goal="Return code 2 and print domain errors to stderr",
)
@pytest.mark.parametrize(
    "error",
    [
        NoOutlineError("No structure"),
        InvalidPdfError("Broken PDF"),
    ],
)
def test_main_returns_2_for_known_domain_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    monkeypatch.setattr(cli, "plan_sections", lambda **_: (_ for _ in ()).throw(error))

    exit_code = cli.main(["book.pdf"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "error:" in captured.err


@pytest.mark.case(
    id="UT-CLI-006",
    type="unit",
    requirement="REQ-CLI-ERRORS",
    goal="Return code 1 and print unexpected exceptions to stderr",
)
def test_main_returns_1_for_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "plan_sections",
        lambda **_: (_ for _ in ()).throw(RuntimeError("Unexpected")),
    )

    exit_code = cli.main(["book.pdf"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "unexpected error:" in captured.err
