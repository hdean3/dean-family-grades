#!/usr/bin/env python3
"""
fetch_grades.py — Replaces Azure Logic App
Fetches the latest LCPS Gradebook email from Gmail via IMAP,
parses grade data, writes data/grades.json.

Required env vars:
  GMAIL_USER         — e.g. hal.dean@gmail.com
  GMAIL_APP_PASSWORD — Gmail App Password (not account password)
                       Create at: myaccount.google.com/apppasswords

Run locally:  python scripts/fetch_grades.py
Run in CI:    called by .github/workflows/fetch-grades.yml
"""

import imaplib
import email
import json
import os
import re
import sys
from email.header import decode_header
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("WARNING: beautifulsoup4 not installed. HTML parsing limited.", file=sys.stderr)

# ── Config ────────────────────────────────────────────────────────────────────
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
IMAP_HOST = "imap.gmail.com"
SEARCH_SUBJECT = "Gradebook"
SEARCH_FROM = "lcps.org"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "grades.json"
RAW_DEBUG_PATH = Path(__file__).parent.parent / "data" / "last_email_raw.txt"


def fetch_latest_grade_email() -> str | None:
    """Connect to Gmail via IMAP, return body of latest matching email."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("ERROR: GMAIL_USER and GMAIL_APP_PASSWORD env vars required.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to Gmail as {GMAIL_USER}...")
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    # Search for matching emails
    search_query = f'FROM "{SEARCH_FROM}" SUBJECT "{SEARCH_SUBJECT}"'
    status, msg_ids = mail.search(None, search_query)

    if status != "OK" or not msg_ids[0]:
        # Fallback: subject only
        print(f"No emails from {SEARCH_FROM}. Trying subject-only search...", file=sys.stderr)
        status, msg_ids = mail.search(None, f'SUBJECT "{SEARCH_SUBJECT}"')

    if status != "OK" or not msg_ids[0]:
        print("No Gradebook emails found in inbox.", file=sys.stderr)
        mail.logout()
        return None

    # Get the most recent matching email
    ids = msg_ids[0].split()
    latest_id = ids[-1]
    print(f"Found {len(ids)} matching email(s). Reading most recent (ID {latest_id.decode()})...")

    status, msg_data = mail.fetch(latest_id, "(RFC822)")
    mail.logout()

    if status != "OK":
        print("Failed to fetch email.", file=sys.stderr)
        return None

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    # Extract subject for logging
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")
    print(f"Email subject: {subject}")
    print(f"From: {msg['From']}")
    print(f"Date: {msg['Date']}")

    # Get body (prefer HTML for richer parsing, fall back to plain text)
    html_body = None
    text_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" and html_body is None:
                html_body = part.get_payload(decode=True).decode("utf-8", errors="replace")
            elif content_type == "text/plain" and text_body is None:
                text_body = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        if "<html" in payload.lower():
            html_body = payload
        else:
            text_body = payload

    # Save raw for debugging
    RAW_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_DEBUG_PATH, "w") as f:
        f.write(f"Subject: {subject}\nFrom: {msg['From']}\nDate: {msg['Date']}\n\n")
        f.write("=== HTML BODY ===\n")
        f.write(html_body or "(none)")
        f.write("\n\n=== TEXT BODY ===\n")
        f.write(text_body or "(none)")
    print(f"Raw email saved to {RAW_DEBUG_PATH} for debugging.")

    return html_body or text_body


def parse_grades_from_html(html: str) -> list[dict]:
    """Parse grade data from LCPS ParentVUE HTML email."""
    if not BS4_AVAILABLE:
        print("ERROR: beautifulsoup4 required for HTML parsing. pip install beautifulsoup4", file=sys.stderr)
        return []

    soup = BeautifulSoup(html, "html.parser")
    grades = []

    # Strategy 1: Look for tables with course/score columns
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Try to identify column positions from header row
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        subject_col = next((i for i, h in enumerate(headers)
                            if any(k in h for k in ["course", "class", "subject", "name"])), None)
        score_col = next((i for i, h in enumerate(headers)
                          if any(k in h for k in ["grade", "score", "percent", "%", "avg"])), None)

        if subject_col is None and score_col is None and len(headers) >= 2:
            # Assume first col = subject, last numeric col = score
            subject_col = 0
            score_col = -1

        if subject_col is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= abs(score_col or 1):
                continue

            subject_text = cells[subject_col].get_text(strip=True)
            score_text = cells[score_col].get_text(strip=True) if score_col is not None else ""

            # Extract numeric score
            score_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%?", score_text)
            if subject_text and score_match:
                score = float(score_match.group(1))
                if 0 <= score <= 100:
                    grades.append({"subject": subject_text, "score": round(score, 1)})

        if grades:
            print(f"Parsed {len(grades)} grades from HTML table.")
            return grades

    # Strategy 2: Look for "Subject: XX%" patterns in plain text within HTML
    text = soup.get_text()
    return parse_grades_from_text(text)


def parse_grades_from_text(text: str) -> list[dict]:
    """Fallback: extract grades from plain text using regex."""
    grades = []
    # Pattern: "Course Name  94%" or "Course Name: 94.5"
    pattern = re.compile(
        r"([A-Za-z][\w\s&/\-]{2,40?}?)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*%?",
        re.MULTILINE
    )
    for match in pattern.finditer(text):
        subject = match.group(1).strip().rstrip(":-")
        score = float(match.group(2))
        if 0 <= score <= 100 and len(subject) > 2:
            grades.append({"subject": subject, "score": round(score, 1)})

    if grades:
        print(f"Parsed {len(grades)} grades from text (regex fallback).")
    return grades


def parse_grades_from_json(text: str) -> list[dict] | None:
    """Try to parse body as JSON directly (as Logic App expected)."""
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "grades" in data:
            return data["grades"]
    except json.JSONDecodeError:
        pass
    return None


def parse_grades(body: str) -> list[dict]:
    """Try all parsing strategies in order."""
    # 1. Try JSON
    grades = parse_grades_from_json(body)
    if grades:
        print("Parsed grades from JSON body.")
        return grades

    # 2. Try HTML
    if "<html" in body.lower() or "<table" in body.lower():
        grades = parse_grades_from_html(body)
        if grades:
            return grades

    # 3. Regex fallback
    grades = parse_grades_from_text(body)
    return grades


def main():
    body = fetch_latest_grade_email()

    if not body:
        print("No email body retrieved. Keeping existing grades.json.", file=sys.stderr)
        sys.exit(0)

    grades = parse_grades(body)

    if not grades:
        print("WARNING: Could not parse any grades from email.", file=sys.stderr)
        print(f"Check {RAW_DEBUG_PATH} to see the raw email and fix the parser.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(grades, f, indent=2)

    print(f"Wrote {len(grades)} grade records to {OUTPUT_PATH}:")
    for g in grades:
        print(f"  {g['subject']}: {g['score']}")


if __name__ == "__main__":
    main()
