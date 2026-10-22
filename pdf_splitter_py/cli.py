from __future__ import annotations

import argparse
import logging
import sys
import time

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
    started_at = time.perf_counter()

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

    elapsed = time.perf_counter() - started_at
    speed_pages = total_pages / elapsed if elapsed > 0 else 0.0

    print("=" * 58)
    print("PDF Splitter - Conversion Summary")
    print("=" * 58)
    print(f"{'Input pages':<18}: {total_pages}")
    print(f"{'Split mode':<18}: {args.mode}")
    if args.mode == "content":
        print(f"{'Depth':<18}: {depth}")
        print(f"{'Structure source':<18}: {source}")
    else:
        print(f"{'Parts':<18}: {max(1, args.parts)}")
    print(f"{'Written files':<18}: {len(written)}")
    print(f"{'Duration':<18}: {elapsed:.2f}s")
    print(f"{'Conversion speed':<18}: {speed_pages:.2f} pages/s")
    print(f"{'Output directory':<18}: {output_dir}")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
