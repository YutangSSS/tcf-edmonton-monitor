"""Monitor the Edmonton Alliance Francaise TCF page for available slots.

The monitor only alerts when an individual TCF exam row exposes an explicit
booking signal such as ``Available`` or ``Register``.  Aggregate counts of
``SOLD OUT`` and ``Closed`` rows are intentionally ignored because sessions
naturally disappear from the page as their dates pass.
"""

from __future__ import annotations

import re
import sys

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


URL = "https://www.afedmonton.com/en/exams/tcf/"
ALERT_MESSAGE = "Possible new TCF Edmonton slot found. Check the website immediately."
ALERT_EXIT_CODE = 1
ERROR_EXIT_CODE = 2

BOOKING_KEYWORDS = ("Available", "Register", "Purchase", "Book")
BOOKING_KEYWORD_PATTERN = re.compile(
    r"\b(?:" + "|".join(map(re.escape, BOOKING_KEYWORDS)) + r")\b",
    re.IGNORECASE,
)


def fetch_page_html(url: str) -> str:
    """Download the page and return its HTML."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; TCFMonitor/1.0; "
            "+https://github.com/actions)"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def normalize_spaces(value: str) -> str:
    """Collapse HTML whitespace into a readable single-line string."""
    return " ".join(value.split())


def class_tokens(element: Tag) -> set[str]:
    """Return an element's CSS classes in lowercase."""
    return {str(token).lower() for token in element.get("class", [])}


def find_available_exam_rows(html: str) -> list[str]:
    """Return TCF exam rows with an explicit booking signal.

    Availability is evaluated within each exam row.  Static help text elsewhere
    on the page therefore cannot trigger an alert.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.tableRow") or soup.select("tr")
    available_rows: list[str] = []

    for row in rows:
        title_element = row.select_one(".es-exam-title")
        if title_element is None:
            continue

        title = normalize_spaces(title_element.get_text(" ", strip=True))
        if "tcf" not in title.lower():
            continue

        signals: list[str] = []
        status_elements = row.select(".es-status, .es-sold-out")
        for element in status_elements:
            status_text = normalize_spaces(element.get_text(" ", strip=True))
            classes = class_tokens(element)
            if {"es-status-available", "es-status-open"} & classes:
                signals.append(f"status: {status_text or 'available'}")
            elif BOOKING_KEYWORD_PATTERN.search(status_text):
                signals.append(f"status: {status_text}")

        booking_controls = " ".join(
            normalize_spaces(element.get_text(" ", strip=True))
            for element in row.select("a, button, input[type='submit']")
        )
        keyword_match = BOOKING_KEYWORD_PATTERN.search(booking_controls)
        if keyword_match:
            signals.append(f"booking action: {normalize_spaces(booking_controls)}")

        unique_signals = list(dict.fromkeys(signals))
        if unique_signals:
            available_rows.append(f"{title} — {'; '.join(unique_signals)}")

    return available_rows


def main() -> int:
    print(f"Checking: {URL}")

    try:
        html = fetch_page_html(URL)
    except requests.RequestException as error:
        print(f"Monitor error: could not fetch the TCF page: {error}", file=sys.stderr)
        return ERROR_EXIT_CODE

    available_rows = find_available_exam_rows(html)
    print(f"TCF exam rows with explicit availability: {len(available_rows)}")

    if available_rows:
        print("\n" + ALERT_MESSAGE)
        print("Reasons:")
        for row in available_rows:
            print(f"- {row}")
        return ALERT_EXIT_CODE

    print("No explicit availability detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
