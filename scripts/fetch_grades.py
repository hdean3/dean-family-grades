#!/usr/bin/env python3
"""
fetch_grades.py — Fetches Ben's grades from ParentVUE API (primary)
or LCPS Gmail Gradebook email (fallback).

Primary: StudentVUE/Synergy API (real-time, no email delay)
Fallback: Gmail IMAP (daily email from lcps.org)

Required env vars (add to GitHub Actions secrets):
  PARENTVUE_USERNAME   — ParentVUE login username
  PARENTVUE_PASSWORD   — ParentVUE login password
  PARENTVUE_DISTRICT   — District URL, e.g. https://portal.lcps.org

  GMAIL_USER           — hal.dean@gmail.com (fallback only)
  GMAIL_APP_PASSWORD   — Gmail App Password (fallback only)
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

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "grades.json"
RAW_DEBUG_PATH = Path(__file__).parent.parent / "data" / "last_email_raw.txt"

IMAP_HOST = "imap.gmail.com"
LCPS_DISTRICT = os.environ.get("PARENTVUE_DISTRICT", "https://portal.lcps.org")


# ── ParentVUE API (primary) ───────────────────────────────────────────────────

def fetch_via_parentvue() -> list[dict] | None:
    """Fetch grades directly from ParentVUE/Synergy API."""
    username = os.environ.get("PARENTVUE_USERNAME", "")
    password = os.environ.get("PARENTVUE_PASSWORD", "")

    if not username or not password:
        print("ParentVUE credentials not set — falling back to Gmail.", file=sys.stderr)
        return None

    try:
        import studentvue
    except ImportError:
        print("studentvue not installed — falling back to Gmail.", file=sys.stderr)
        return None

    try:
        print(f"Connecting to ParentVUE at {LCPS_DISTRICT}...")
        sv = studentvue.StudentVue(username, password, LCPS_DISTRICT)
        gradebook = sv.get_gradebook()

        grades = []
        for course in gradebook.get("Gradebook", {}).get("Courses", {}).get("Course", []):
            name = course.get("@Title", "Unknown")
            # Period from @Period attribute, e.g. "1"
            mark = course.get("Marks", {}).get("Mark", {})
            if isinstance(mark, list):
                mark = mark[0]
            score_str = mark.get("@CalculatedScoreRaw", "")
            try:
                score = round(float(score_str), 1)
                grades.append({"subject": name, "score": score})
                print(f"  {name}: {score}")
            except (ValueError, TypeError):
                pass

        if grades:
            print(f"ParentVUE: fetched {len(grades)} courses.")
            return grades
    except Exception as e:
        print(f"ParentVUE API error: {e} — falling back to Gmail.", file=sys.stderr)

    return None


# ── Gmail IMAP fallback ───────────────────────────────────────────────────────

def fetch_latest_grade_email() -> str | None:
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_pass:
        print("ERROR: No credentials available (ParentVUE or Gmail).", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching Gmail for LCPS Gradebook email...")
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(gmail_user, gmail_pass)
    mail.select("inbox")

    # Try sender + subject first
    status, msg_ids = mail.search(None, 'FROM "lcps.org" SUBJECT "Gradebook"')
    if status != "OK" or not msg_ids[0]:
        status, msg_ids = mail.search(None, 'SUBJECT "Gradebook"')
    if status != "OK" or not msg_ids[0]:
        status, msg_ids = mail.search(None, 'SUBJECT "ParentVUE"')

    if status != "OK" or not msg_ids[0]:
        print("No matching emails found.", file=sys.stderr)
        mail.logout()
        return None

    latest_id = msg_ids[0].split()[-1]
    status, msg_data = mail.fetch(latest_id, "(RFC822)")
    mail.logout()

    msg = email.message_from_bytes(msg_data[0][1])
    subj, enc = decode_header(msg["Subject"])[0]
    if isinstance(subj, bytes):
        subj = subj.decode(enc or "utf-8")
    print(f"Email: {subj} | From: {msg['From']} | Date: {msg['Date']}")

    html_body = text_body = None
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html" and not html_body:
                html_body = part.get_payload(decode=True).decode("utf-8", errors="replace")
            elif ct == "text/plain" and not text_body:
                text_body = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        html_body = payload if "<html" in payload.lower() else None
        text_body = payload if not html_body else None

    RAW_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_DEBUG_PATH, "w") as f:
        f.write(f"Subject: {subj}\nFrom: {msg['From']}\nDate: {msg['Date']}\n\n")
        f.write("=== HTML ===\n")
        f.write(html_body or "(none)")
        f.write("\n\n=== TEXT ===\n")
        f.write(text_body or "(none)")

    return html_body or text_body


def parse_lcps_email(body: str) -> list[dict]:
    """
    Parse LCPS ParentVUE Gradebook email.

    Email table format (HTML):
      Col 0: "Marceau, A /Randlett Env Science(1)"
      Col 1: "87%"
      Col 2: "MP3"
      Col 3: "B+"
      Col 4: "1 missing assignments"

    Course name extraction:
      "LastName, F /CourseName(period)" -> "CourseName"
    """
    if not BS4_AVAILABLE:
        return parse_lcps_text(body)

    soup = BeautifulSoup(body, "html.parser")
    seen = {}  # course -> score; deduplicates multiple matched rows per course

    for row in soup.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 2:
            continue

        # Look for a cell that is exactly "87%" — a standalone percentage score
        score = None
        for cell in cells:
            pct_match = re.match(r"^(\d{1,3})%$", cell)
            if pct_match:
                score = int(pct_match.group(1))
                break

        if score is None or not (0 <= score <= 100):
            continue

        # The course name is in the first cell
        raw_name = cells[0]

        # Skip garbled rows where the entire row was concatenated into cells[0]
        # (these contain "%" from the score column bleeding into the name column)
        if "%" in raw_name:
            continue

        # Extract course name from "LastName, F /CourseName(period)"
        if "/" in raw_name:
            course = raw_name.split("/", 1)[1].strip()
        else:
            # No slash: strip "LastName, F " teacher prefix if present
            course = re.sub(r"^[A-Z][A-Za-z'-]+,\s+[A-Z]\s+", "", raw_name).strip()

        # Strip trailing period indicator: "Env Science(1)" -> "Env Science"
        course = re.sub(r"\s*\(\d+\)\s*$", "", course).strip()
        # Strip bare trailing digit: "Env Science 1" -> "Env Science"
        course = re.sub(r"\s+\d+$", "", course).strip()

        if not course or len(course) < 2:
            continue

        # Deduplicate: first clean extraction wins
        if course not in seen:
            seen[course] = score
            print(f"  {course}: {score}")

    if seen:
        grades = [{"subject": k, "score": v} for k, v in seen.items()]
        print(f"Parsed {len(grades)} courses from LCPS email HTML.")
        return grades

    # Fallback to text parsing
    return parse_lcps_text(soup.get_text())


def parse_lcps_text(text: str) -> list[dict]:
    """Regex fallback for plain text LCPS email."""
    grades = []
    # Match: anything ending with /CourseName(period) followed by score%
    pattern = re.compile(
        r"/([^(/\n]+?)(?:\(\d+\))?\s+(\d{1,3})%",
        re.MULTILINE
    )
    for m in pattern.finditer(text):
        course = m.group(1).strip()
        score = int(m.group(2))
        if 0 <= score <= 100 and len(course) > 2:
            grades.append({"subject": course, "score": score})
            print(f"  {course}: {score}")
    if grades:
        print(f"Parsed {len(grades)} courses from text (regex fallback).")
    return grades


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Try ParentVUE API first (real-time)
    grades = fetch_via_parentvue()

    # Fall back to Gmail email parsing
    if not grades:
        body = fetch_latest_grade_email()
        if not body:
            print("No data source available. Keeping existing grades.json.", file=sys.stderr)
            sys.exit(0)
        if "<html" in body.lower() or "<table" in body.lower():
            grades = parse_lcps_email(body)
        else:
            grades = parse_lcps_text(body)

    if not grades:
        print("WARNING: Could not parse any grades.", file=sys.stderr)
        print(f"Check {RAW_DEBUG_PATH} for raw email content.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(grades, f, indent=2)
    print(f"\nWrote {len(grades)} courses to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
