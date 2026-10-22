"""Generate a synthetic, deliberately messy customer list.

All data is made up: names come from short fixed lists, emails use the reserved
example.com domain, and phone numbers use the 555-01xx range set aside for
fiction. Run it again with the same seed to get the same file.
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

FIRST = [
    "Anna",
    "Ben",
    "Carla",
    "David",
    "Elena",
    "Frank",
    "Grace",
    "Hugo",
    "Iris",
    "Jakub",
    "Karen",
    "Leo",
    "Maria",
    "Nora",
    "Oscar",
    "Petra",
    "Quinn",
    "Rosa",
    "Sam",
    "Tomas",
]
LAST = [
    "Novak",
    "Smith",
    "Garcia",
    "Muller",
    "Rossi",
    "Kowalski",
    "Brown",
    "Dvorak",
    "Lopez",
    "Weber",
    "Moreau",
    "Jensen",
    "Horvat",
    "Silva",
    "Taylor",
]
CITIES = ["Prague", "Brno", "Berlin", "Vienna", "Austin", "Denver", "Lyon", "Krakow"]
PLANS = ["Basic", "Pro", "Team"]


def messy_date(d: date, rng: random.Random) -> str:
    style = rng.randrange(7)
    return [
        d.isoformat(),
        d.strftime("%d.%m.%Y"),
        d.strftime("%m/%d/%Y"),
        d.strftime("%b %d, %Y"),
        d.strftime("%Y/%m/%d"),
        f"  {d.isoformat()} ",
        "31.02.2025" if rng.random() < 0.5 else "next week",
    ][style if style < 6 or rng.random() < 0.3 else 0]


def messy_phone(rng: random.Random) -> str:
    area = rng.choice(["212", "312", "415", "512", "720"])
    line = f"01{rng.randrange(100):02d}"
    style = rng.randrange(6)
    if style == 5 and rng.random() < 0.4:
        return f"555-{line}"
    return [
        f"({area}) 555-{line}",
        f"{area}.555.{line}",
        f"+1 {area} 555 {line}",
        f"001{area}555{line}",
        f"{area}-555-{line}",
        f"{area}555{line}",
    ][style]


def messy_email(first: str, last: str, rng: random.Random) -> str:
    email = f"{first}.{last}@example.com"
    roll = rng.random()
    if roll < 0.2:
        return email.upper()
    if roll < 0.3:
        return f"  {email} "
    if roll < 0.34:
        return email.replace("@", " at ")
    return email.lower()


def main(path: Path, count: int = 500, seed: int = 7) -> None:
    rng = random.Random(seed)
    headers = [" Customer ID", "Full  Name", "E-mail", "Phone #", "Signup Date", "City ", "Plan"]
    rows: list[list[str]] = []
    start = date(2024, 1, 1)
    for n in range(1, count + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        name = f"{first}  {last}" if rng.random() < 0.15 else f"{first} {last}"
        row = [
            f"C{n:04d}",
            name,
            messy_email(first, last, rng),
            messy_phone(rng) if rng.random() > 0.05 else "",
            messy_date(start + timedelta(days=rng.randrange(900)), rng),
            rng.choice(CITIES) + (" " if rng.random() < 0.2 else ""),
            rng.choice(PLANS),
        ]
        if rng.random() < 0.03:
            row[0] = ""
        rows.append(row)
        if rng.random() < 0.06:
            dup = list(row)
            dup[2] = dup[2].upper()
            rows.append(dup)
        if rng.random() < 0.01:
            rows.append([""] * len(headers))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "samples/customers_dirty.csv"))
