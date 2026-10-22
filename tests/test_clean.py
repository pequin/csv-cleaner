from datetime import date

import pytest

from csv_cleaner.clean import (
    Options,
    clean_rows,
    normalize_email,
    normalize_header,
    normalize_phone,
    parse_date,
    unique_headers,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Customer ID", "customer_id"),
        ("Full  Name", "full_name"),
        ("E-mail", "e_mail"),
        ("Phone #", "phone"),
        ("Café", "cafe"),
        ("###", "column"),
    ],
)
def test_normalize_header(raw, expected):
    assert normalize_header(raw) == expected


def test_unique_headers_adds_suffix():
    assert unique_headers(["Name", "name ", "NAME"]) == ["name", "name_2", "name_3"]


@pytest.mark.parametrize(
    "raw",
    ["2026-03-04", "2026/03/04", "04.03.2026", "03/04/2026", "Mar 04, 2026", " 2026-03-04 "],
)
def test_parse_date_formats(raw):
    assert parse_date(raw) == date(2026, 3, 4)


def test_parse_date_rejects_impossible_and_free_text():
    assert parse_date("31.02.2025") is None
    assert parse_date("next week") is None
    assert parse_date("") is None


def test_parse_date_month_first_reads_dotted_dates_as_us_order():
    assert parse_date("03.04.2026", day_first=False) == date(2026, 3, 4)
    assert parse_date("03-04-2026", day_first=False) == date(2026, 3, 4)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("(212) 555-0142", "+12125550142"),
        ("212.555.0142", "+12125550142"),
        ("+1 212 555 0142", "+12125550142"),
        ("0012125550142", "+12125550142"),
        ("+420 601 555 014", "+420601555014"),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_normalize_phone_rejects_short_numbers():
    assert normalize_phone("555-0142") is None


def test_normalize_phone_uses_default_country():
    assert normalize_phone("601 555 0142", default_country="44") == "+446015550142"


def test_normalize_email():
    assert normalize_email("  Anna.Novak@Example.COM ") == "anna.novak@example.com"
    assert normalize_email("anna at example.com") is None


def test_clean_rows_reports_instead_of_dropping():
    headers = ["ID", "E-mail", "Signup Date", "Phone"]
    rows = [
        ["1", "A@example.com", "01.02.2026", "212 555 0100"],
        ["2", "bad email", "soon", "555"],
        ["", "", "", ""],
        ["1", "a@example.com ", "2026-02-01", "(212) 555-0100"],
        ["3", "c@example.com", "", "", "stray"],
    ]
    opts = Options(
        date_columns=("signup_date",),
        phone_columns=("phone",),
        email_columns=("e_mail",),
        required=("signup_date",),
        key=("e_mail",),
    )
    result = clean_rows(headers, rows, opts)

    assert result.headers == ["id", "e_mail", "signup_date", "phone"]
    assert result.rows_in == 5
    assert result.duplicates == 1
    assert [r["id"] for r in result.rows] == ["1", "2", "3"]
    assert result.rows[0] == {
        "id": "1",
        "e_mail": "a@example.com",
        "signup_date": "2026-02-01",
        "phone": "+12125550100",
    }
    # The bad row is kept as is, and each problem is listed with its row number.
    assert result.rows[1]["e_mail"] == "bad email"
    problems = {(i.row, i.problem) for i in result.issues}
    assert problems == {
        (3, "unknown date format"),
        (3, "phone looks wrong"),
        (3, "invalid email"),
        (4, "empty row skipped"),
        (5, "duplicate removed"),
        (6, "extra cells ignored"),
        (6, "required value missing"),
    }
