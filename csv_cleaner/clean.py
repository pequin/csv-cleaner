"""Core cleaning rules.

Every function here is pure: it takes values in and returns values out, so the
rules are easy to test and reuse outside the command line tool.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%Y%m%d",
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
_SPACES_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^0-9a-z]+")


def normalize_header(name: str) -> str:
    """Turn a column title such as ' E-mail Address ' into 'e_mail_address'."""
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = _NON_WORD_RE.sub("_", text).strip("_")
    return text or "column"


def unique_headers(names: list[str]) -> list[str]:
    """Normalize headers and add a numeric suffix to repeated names."""
    seen: dict[str, int] = {}
    result = []
    for raw in names:
        name = normalize_header(raw)
        count = seen.get(name, 0)
        seen[name] = count + 1
        result.append(name if count == 0 else f"{name}_{count + 1}")
    return result


def squeeze(value: str) -> str:
    """Trim the value and collapse runs of whitespace into one space."""
    return _SPACES_RE.sub(" ", value).strip()


def parse_date(value: str, day_first: bool = True) -> date | None:
    """Parse a date written in one of the common formats.

    Slash dates such as 03/04/2026 are read in US order (month/day/year).
    Dotted and dashed dates such as 03.04.2026 are read as day.month.year,
    the usual European order, unless ``day_first`` is False.
    """
    text = squeeze(value)
    if not text:
        return None
    formats = DATE_FORMATS
    if not day_first:
        swap = {"%d.%m.%Y": "%m.%d.%Y", "%d-%m-%Y": "%m-%d-%Y"}
        formats = tuple(swap.get(f, f) for f in DATE_FORMATS)
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_phone(value: str, default_country: str = "1") -> str | None:
    """Return the phone number as +<country><number>, or None if it looks wrong.

    Accepts spaces, dots, dashes, and brackets. A 10-digit number gets the
    default country code. A leading 00 is treated as an international prefix.
    """
    text = squeeze(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.startswith("+"):
        pass
    elif digits.startswith("00"):
        digits = digits[2:]
    elif len(digits) == 10:
        digits = default_country + digits
    if not 11 <= len(digits) <= 15:
        return None
    return "+" + digits


def normalize_email(value: str) -> str | None:
    """Lowercase and trim an email address; return None if it is not valid."""
    text = squeeze(value).lower()
    if not text or not EMAIL_RE.match(text):
        return None
    return text


@dataclass
class Issue:
    """A problem found in one input row."""

    row: int
    column: str
    value: str
    problem: str


@dataclass
class Result:
    """The cleaned rows plus everything the cleaner did not trust."""

    headers: list[str]
    rows: list[dict[str, str]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    duplicates: int = 0
    rows_in: int = 0


@dataclass
class Options:
    """Which columns get which rule."""

    date_columns: tuple[str, ...] = ()
    phone_columns: tuple[str, ...] = ()
    email_columns: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    key: tuple[str, ...] = ()
    default_country: str = "1"
    day_first: bool = True


def clean_rows(raw_headers: list[str], raw_rows: list[list[str]], opts: Options) -> Result:
    """Clean every row and collect issues instead of dropping data silently.

    Row numbers in issues match the input file, counting the header as row 1.
    """
    headers = unique_headers(raw_headers)
    result = Result(headers=headers)
    seen_keys: dict[tuple[str, ...], int] = {}

    for index, raw in enumerate(raw_rows, start=2):
        result.rows_in += 1
        padded = list(raw) + [""] * (len(headers) - len(raw))
        if len(raw) > len(headers):
            extra = " | ".join(squeeze(v) for v in raw[len(headers) :] if squeeze(v))
            if extra:
                result.issues.append(Issue(index, "", extra, "extra cells ignored"))
        row = {h: squeeze(v) for h, v in zip(headers, padded, strict=False)}
        if not any(row.values()):
            result.issues.append(Issue(index, "", "", "empty row skipped"))
            continue

        for col in opts.date_columns:
            value = row.get(col, "")
            if value:
                parsed = parse_date(value, opts.day_first)
                if parsed is None:
                    result.issues.append(Issue(index, col, value, "unknown date format"))
                else:
                    row[col] = parsed.isoformat()
        for col in opts.phone_columns:
            value = row.get(col, "")
            if value:
                phone = normalize_phone(value, opts.default_country)
                if phone is None:
                    result.issues.append(Issue(index, col, value, "phone looks wrong"))
                else:
                    row[col] = phone
        for col in opts.email_columns:
            value = row.get(col, "")
            if value:
                email = normalize_email(value)
                if email is None:
                    result.issues.append(Issue(index, col, value, "invalid email"))
                else:
                    row[col] = email
        for col in opts.required:
            if not row.get(col):
                result.issues.append(Issue(index, col, "", "required value missing"))

        if opts.key:
            key = tuple(row.get(col, "").lower() for col in opts.key)
            if any(key):
                if key in seen_keys:
                    result.duplicates += 1
                    first = seen_keys[key]
                    shown = " / ".join(row.get(col, "") for col in opts.key)
                    value = f"{shown} (first seen in row {first})"
                    result.issues.append(
                        Issue(index, ",".join(opts.key), value, "duplicate removed")
                    )
                    continue
                seen_keys[key] = index
        result.rows.append(row)
    return result
