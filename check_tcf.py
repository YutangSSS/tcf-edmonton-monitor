"""Monitor the Edmonton Alliance Francaise TCF page for possible new slots.

The script is intentionally small and conservative:
- fetch the public TCF page;
- extract readable text;
- look for new exam months beyond a known baseline;
- compare SOLD OUT / Closed counts against a known baseline;
- look for booking-related words near exam rows.

If a possible slot is found, the script exits with code 1 so GitHub Actions
marks the run as failed and sends a notification when enabled.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Iterable

import requests
from bs4 import BeautifulSoup


URL = "https://www.afedmonton.com/en/exams/tcf/"
ALERT_MESSAGE = "Possible new TCF Edmonton slot found. Check the website immediately."

# Baseline from the visible page as of 2026-07-04.
# Override these in GitHub Actions env if the page changes and you want a new baseline.
DEFAULT_EXPECTED_MONTHS = "June 2026,July 2026,August 2026"
DEFAULT_MIN_SOLD_OUT_COUNT = 34
DEFAULT_MIN_CLOSED_COUNT = 28

BOOKING_KEYWORDS = ("Register", "Available", "Purchase", "Book")
FULL_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
MONTH_ABBREVIATIONS = {
    "jan": "January",
    "feb": "February",
    "mar": "March",
    "apr": "April",
    "may": "May",
    "jun": "June",
    "jul": "July",
    "aug": "August",
    "sep": "September",
    "sept": "September",
    "oct": "October",
    "nov": "November",
    "dec": "December",
}
FULL_MONTH_PATTERN = "|".join(FULL_MONTHS)
SHORT_MONTH_PATTERN = "|".join(MONTH_ABBREVIATIONS)
WEEKDAY_PATTERN = (
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"Mon|Tue|Wed|Thu|Fri|Sat|Sun"
)
MONTH_YEAR_PATTERN = re.compile(
    rf"\b({FULL_MONTH_PATTERN})\s+20\d{{2}}\b",
    re.IGNORECASE,
)
FULL_EXAM_DATE_PATTERN = re.compile(
    rf"\b({FULL_MONTH_PATTERN})\s+\d{{1,2}},\s*(20\d{{2}})\b",
    re.IGNORECASE,
)
SHORT_EXAM_DATE_PATTERN = re.compile(
    rf"\b(?:{WEEKDAY_PATTERN})\s+\d{{1,2}}\s+({SHORT_MONTH_PATTERN})\s+(20\d{{2}})\b",
    re.IGNORECASE,
)


def fetch_page_text(url: str) -> str:
    """Download the page and return normalized visible text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; TCFMonitor/1.0; "
            "+https://github.com/actions)"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return soup.get_text("\n", strip=True)


def env_list(name: str, default: str) -> set[str]:
    """Read a comma-separated environment variable into normalized values."""
    raw_value = os.getenv(name, default)
    return {item.strip().lower() for item in raw_value.split(",") if item.strip()}


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a safe default."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        print(f"Invalid {name}={raw_value!r}; using default {default}.")
        return default


def find_months(text: str) -> set[str]:
    """Find exam months from month headings and exam date rows."""
    months = set()
    for match in MONTH_YEAR_PATTERN.finditer(text):
        month, year = match.group(1), match.group(0)[-4:]
        months.add(f"{month.title()} {year}")

    for match in FULL_EXAM_DATE_PATTERN.finditer(text):
        month, year = match.group(1), match.group(2)
        months.add(f"{month.title()} {year}")

    for match in SHORT_EXAM_DATE_PATTERN.finditer(text):
        month = MONTH_ABBREVIATIONS[match.group(1).lower()]
        year = match.group(2)
        months.add(f"{month} {year}")

    return months


def count_phrase(text: str, phrase: str) -> int:
    """Count a phrase case-insensitively."""
    return len(re.findall(re.escape(phrase), text, flags=re.IGNORECASE))


def keyword_hits_near_tcf_rows(lines: Iterable[str]) -> list[str]:
    """Find booking words close to TCF exam rows, skipping static help text."""
    hits: list[str] = []
    recent_lines: list[str] = []

    for line in lines:
        clean_line = " ".join(line.split())
        if not clean_line:
            continue

        recent_lines.append(clean_line)
        recent_lines = recent_lines[-6:]
        context = " ".join(recent_lines)

        if "TCF Canada" not in context:
            continue

        for keyword in BOOKING_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", clean_line, re.IGNORECASE):
                hits.append(clean_line)
                break

    return hits


def main() -> int:
    print(f"Checking: {URL}")
    text = fetch_page_text(URL)
    lines = text.splitlines()

    expected_months = env_list("EXPECTED_MONTHS", DEFAULT_EXPECTED_MONTHS)
    min_sold_out_count = env_int("MIN_SOLD_OUT_COUNT", DEFAULT_MIN_SOLD_OUT_COUNT)
    min_closed_count = env_int("MIN_CLOSED_COUNT", DEFAULT_MIN_CLOSED_COUNT)

    found_months = find_months(text)
    new_months = sorted(
        month for month in found_months if month.lower() not in expected_months
    )

    sold_out_count = count_phrase(text, "SOLD OUT")
    closed_count = count_phrase(text, "Closed")
    keyword_hits = keyword_hits_near_tcf_rows(lines)

    print(f"Months found: {', '.join(sorted(found_months)) or 'none'}")
    print(f"SOLD OUT count: {sold_out_count} (baseline minimum: {min_sold_out_count})")
    print(f"Closed count: {closed_count} (baseline minimum: {min_closed_count})")

    reasons: list[str] = []
    if new_months:
        reasons.append(f"New month(s) found: {', '.join(new_months)}")
    if sold_out_count < min_sold_out_count:
        reasons.append("SOLD OUT count decreased.")
    if closed_count < min_closed_count:
        reasons.append("Closed count decreased.")
    if keyword_hits:
        reasons.append(
            "Booking keyword(s) found near TCF exam rows: "
            + " | ".join(keyword_hits[:5])
        )

    if reasons:
        print("\n" + ALERT_MESSAGE)
        print("Reasons:")
        for reason in reasons:
            print(f"- {reason}")
        return 1

    print("No possible new TCF Edmonton slot detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
