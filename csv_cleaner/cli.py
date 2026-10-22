"""Command line entry point: ``python -m csv_cleaner input.csv -o output.xlsx``."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .clean import Options, clean_rows
from .io import read_csv, write_issues, write_table


def _columns(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in value.split(",") if v.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv_cleaner",
        description="Clean a messy CSV file and write a report of rows that need a look.",
    )
    parser.add_argument("input", type=Path, help="CSV file to clean")
    parser.add_argument(
        "-o", "--output", type=Path, help="output .csv or .xlsx (default: <input>_clean.csv)"
    )
    parser.add_argument("--report", type=Path, help="issue report (default: <output>_issues.csv)")
    parser.add_argument("--dates", type=_columns, default=(), help="date columns, comma separated")
    parser.add_argument("--phones", type=_columns, default=(), help="phone columns")
    parser.add_argument("--emails", type=_columns, default=(), help="email columns")
    parser.add_argument("--required", type=_columns, default=(), help="columns that must be set")
    parser.add_argument(
        "--key", type=_columns, default=(), help="columns that identify a duplicate"
    )
    parser.add_argument(
        "--country", default="1", help="country code for 10-digit phones (default 1)"
    )
    parser.add_argument(
        "--month-first",
        action="store_true",
        help="read 03-04-2026 and 03.04.2026 as March 4 (default: day first)",
    )
    parser.add_argument("--encoding", help="input encoding (default: try UTF-8, then cp1252)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or args.input.with_name(args.input.stem + "_clean.csv")
    report = args.report or output.with_name(output.stem + "_issues" + output.suffix)

    try:
        raw_headers, raw_rows = read_csv(args.input, args.encoding)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    opts = Options(
        date_columns=args.dates,
        phone_columns=args.phones,
        email_columns=args.emails,
        required=args.required,
        key=args.key,
        default_country=args.country,
        day_first=not args.month_first,
    )
    result = clean_rows(raw_headers, raw_rows, opts)
    known = set(result.headers)
    unknown = [
        c
        for c in (*args.dates, *args.phones, *args.emails, *args.required, *args.key)
        if c not in known
    ]
    if unknown:
        print(f"error: unknown column(s): {', '.join(sorted(set(unknown)))}", file=sys.stderr)
        print(f"columns after cleanup: {', '.join(result.headers)}", file=sys.stderr)
        return 2

    write_table(output, result.headers, result.rows)
    write_issues(report, result.issues)

    print(f"rows in:     {result.rows_in}")
    print(f"rows out:    {len(result.rows)}")
    print(f"duplicates:  {result.duplicates} removed")
    print(f"issues:      {len(result.issues)}")
    for problem, count in Counter(i.problem for i in result.issues).most_common():
        print(f"  {count:4d}  {problem}")
    print(f"saved {output}")
    print(f"saved {report}")
    return 0
