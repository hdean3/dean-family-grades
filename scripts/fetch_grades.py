#!/usr/bin/env python3
"""
fetch_grades.py — Fetches Ben's grades from ParentVUE API (primary)
or LCPS Gmail Gradebook email (fallback).

Primary: StudentVUE/Synergy API (real-time, no email delay)
  Step 1 — ChildList: enumerate students on the account, find Ben by first name
  Step 2 — Gradebook(ChildIntID=...): fetch his courses specifically

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

# First name to look for in ChildList (case-insensitive)
TARGET_STUDENT = os.environ.get("PARENTVUE_STUDENT_NAME", "Ben")


# ── ParentVUE API (primary — direct SOAP, no studentvue library) ─────────────

def _fix_xml_entities(s: str) -> str:
    """Replace bare & not part of a valid XML entity reference."""
    return re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', s)


def fetch_via_parentvue() -> list[dict] | None:
    """
    Fetch grades via direct SOAP to LCPS Synergy (parent=1 account).

    Known LCPS limitation: Synergy ignores all child-selection params
    (ChildGU, StudentGU, OrgYearGU) and always returns the default child's
    gradebook. For multi-child accounts this is unreliable — Gmail fallback
    is preferred for LCPS until a session-based approach is implemented.

    Returns a list of grade dicts if the default child is secondary
    (percentage-based gradebook), otherwise None to trigger fallback.
    """
    import urllib.request as _urlreq
    import xml.etree.ElementTree as ET

    username = os.environ.get("PARENTVUE_USERNAME", "")
    password = os.environ.get("PARENTVUE_PASSWORD", "")

    if not username or not password:
        return None

    def xml_esc(s: str) -> str:
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def soap_call(method_name: str, param_str: str) -> ET.Element | None:
        body = (
            "<?xml version='1.0' encoding='utf-8'?>"
            '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Body>'
            '<ProcessWebServiceRequest xmlns="http://edupoint.com/webservices/">'
            f'<userID>{xml_esc(username)}</userID>'
            f'<password>{xml_esc(password)}</password>'
            '<skipLoginLog>1</skipLoginLog>'
            '<parent>1</parent>'
            '<webServiceHandleName>PXPWebServices</webServiceHandleName>'
            f'<methodName>{method_name}</methodName>'
            f'<paramStr>{param_str}</paramStr>'
            '</ProcessWebServiceRequest>'
            '</soap:Body>'
            '</soap:Envelope>'
        ).encode('utf-8')
        req = _urlreq.Request(
            f"{LCPS_DISTRICT}/Service/PXPCommunication.asmx",
            data=body,
            headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://edupoint.com/webservices/ProcessWebServiceRequest',
            },
            method='POST'
        )
        with _urlreq.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        outer = ET.fromstring(_fix_xml_entities(raw))
        # Python ET sometimes fails namespace-qualified find() inside SOAP envelope
        result_el = next((el for el in outer.iter() if el.tag.endswith('ProcessWebServiceRequestResult')), None)
        if not result_el or not result_el.text:
            return None
        return ET.fromstring(_fix_xml_entities(result_el.text.strip()))

    try:
        # Portal URL: /PXP2_Gradebook.aspx?AGU=1&studentGU=...
        # AGU appears to be a 0-based child index: Bailey=0, Ben=1, Riley=2
        # studentGU in the URL is stale (Bailey's GU) — portal uses session for child selection.
        # Try AGU=1 as SOAP param to select Ben (second child).
        gradebook = None
        for params in [
            '&lt;Parms&gt;&lt;AGU&gt;1&lt;/AGU&gt;&lt;/Parms&gt;',
            '&lt;Parms&gt;&lt;/Parms&gt;',
        ]:
            gb = soap_call('Gradebook', params)
            if gb is not None and gb.tag != 'RT_ERROR' and gb.get('Type') != 'Standards':
                gradebook = gb
                print(f"Gradebook params matched: {params[:60]}")
                break

        if gradebook is None or gradebook.tag == 'RT_ERROR':
            return None

        if gradebook.get('Type') == 'Standards':
            print("ParentVUE: got elementary gradebook — skipping.", file=sys.stderr)
            return None

        grades = []
        for course in gradebook.findall('.//Course'):
            name = course.get('Title', 'Unknown')
            score_str = course.get('CalculatedScoreRaw', '') or course.get('GradeCalculatedScoreRaw', '')
            if not score_str:
                mark = course.find('.//Mark')
                score_str = mark.get('CalculatedScoreRaw', '') if mark is not None else ''
            try:
                score = round(float(score_str), 1)
            except (ValueError, TypeError):
                continue
            has_missing = course.get('HasMissingAssignments', 'false').lower() == 'true'
            missing = 1 if has_missing else sum(
                1 for a in course.findall('.//AssignmentGradeCalc')
                if a.get('Points', '').strip() in ('', 'Not Graded')
                and a.get('PointsPossible', '0').strip() not in ('0', '')
            )
            grades.append({"subject": name, "score": score, "missing": missing})
            print(f"  {name}: {score} ({missing} missing)")

        if grades:
            print(f"ParentVUE: fetched {len(grades)} courses.")
            return grades
        return None

    except Exception as e:
        print(f"ParentVUE API error: {e}", file=sys.stderr)
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

        # Extract missing assignments count: "1 missing assignments" -> 1
        missing = 0
        for cell in cells:
            miss_match = re.match(r"^(\d+) missing", cell)
            if miss_match:
                missing = int(miss_match.group(1))
                break

        # Deduplicate: first clean extraction wins
        if course not in seen:
            seen[course] = {"score": score, "missing": missing}
            print(f"  {course}: {score} ({missing} missing)")

    if seen:
        grades = [{"subject": k, "score": v["score"], "missing": v["missing"]} for k, v in seen.items()]
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
            grades.append({"subject": course, "score": score, "missing": 0})
            print(f"  {course}: {score}")
    if grades:
        print(f"Parsed {len(grades)} courses from text (regex fallback).")
    return grades


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Try ParentVUE API first (real-time)
    grades = fetch_via_parentvue()

    # Fall back to Gmail email parsing — but ONLY if no grades.json exists yet.
    # If grades.json already has data (e.g. manually corrected), keep it.
    # The LCPS email can be stale or slightly inaccurate; don't let it overwrite
    # verified grades. Re-enable email fallback once the API works for Ben.
    if not grades:
        if OUTPUT_PATH.exists():
            print("ParentVUE unavailable. grades.json already exists — keeping current data.", file=sys.stderr)
            sys.exit(0)
        body = fetch_latest_grade_email()
        if not body:
            print("No data source available.", file=sys.stderr)
            sys.exit(0)
        if "<html" in body.lower() or "<table" in body.lower():
            grades = parse_lcps_email(body)
        else:
            grades = parse_lcps_text(body)

    if not grades:
        print("WARNING: Could not parse any grades.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(grades, f, indent=2)
    print(f"\nWrote {len(grades)} courses to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
