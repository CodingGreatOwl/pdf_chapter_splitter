from __future__ import annotations

import argparse
import logging
import sys

from .splitter import default_output_dir, extract, plan_sections
from .types import InvalidPdfError, NoOutlineError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-splitter",
        description="Split a PDF by outline depth, detected headings, or equal parts.",
    )
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["content", "length"],
        default="content",
        help="Split by content (outline/headings) or by equal length",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=1,
        help="Outline/heading depth for content mode (default: 1)",
    )
    parser.add_argument(
        "-p",
        "--parts",
        type=int,
        default=4,
        help="Equal parts count in length mode (default: 4)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Output directory (default: sibling folder named after the PDF)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    args = build_parser().parse_args(argv)

    output_dir = args.output_dir or default_output_dir(args.input)
    depth = max(1, args.depth)

    try:
        chapters, total_pages, source = plan_sections(
            path=args.input,
            mode=args.mode,
            depth=depth,
            parts=max(1, args.parts),
        )
        written = extract(
            path=args.input,
            source_name=args.input.split("/")[-1],
            chapters=chapters,
            numbered=args.mode == "length",
            output_dir=output_dir,
        )
    except (NoOutlineError, InvalidPdfError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # pragma: no cover
        print(f"unexpected error: {error}", file=sys.stderr)
        return 1

    print(f"Input pages: {total_pages}")
    print(f"Split mode: {args.mode}")
    if args.mode == "content":
        print(f"Depth: {depth}")
        print(f"Structure source: {source}")
    else:
        print(f"Parts: {max(1, args.parts)}")
    print(f"Written files: {len(written)}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
