"""Reading and writing CSV and Excel files."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from .clean import Issue

ENCODINGS = ("utf-8-sig", "cp1252")


def read_csv(path: Path, encoding: str | None = None) -> tuple[list[str], list[list[str]]]:
    """Read a CSV file, guessing the delimiter and the encoding."""
    data = path.read_bytes()
    text = None
    for enc in (encoding,) if encoding else ENCODINGS:
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        msg = f"cannot decode {path}; pass --encoding"
        raise ValueError(msg)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    if not rows:
        msg = f"{path} is empty"
        raise ValueError(msg)
    return rows[0], rows[1:]


def write_table(path: Path, headers: list[str], rows: Iterable[dict[str, str]]) -> None:
    """Write rows to .csv or .xlsx, depending on the file extension."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".xlsx":
        _write_xlsx(path, headers, [[row.get(h, "") for h in headers] for row in rows])
        return
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_issues(path: Path, issues: list[Issue]) -> None:
    """Write the issue report as CSV or Excel."""
    headers = ["row", "column", "value", "problem"]
    rows = [
        {"row": str(i.row), "column": i.column, "value": i.value, "problem": i.problem}
        for i in issues
    ]
    write_table(path, headers, rows)


def _write_xlsx(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    for col_cells in ws.columns:
        width = max(len(str(c.value or "")) for c in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(width + 2, 8), 50)
    wb.save(path)
