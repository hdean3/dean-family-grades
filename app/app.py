import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path

# --- 1. CONFIGURATION ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Ben Dean")
rates = {
    "A+": 150.0, "A": 125.0, "A-": 100.0,
    "B+": 75.0,  "B": 50.0,  "B-": 25.0,
}

GMU_THRESHOLD = 3.25   # GMU guaranteed admission by end of junior year

VCCS_SCHOOLS = [
    {"school": "George Mason University",  "min_gpa": 3.0, "notes": "If direct admission missed, NOVA→GMU transfer. Same destination."},
    {"school": "James Madison University", "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Virginia Commonwealth",    "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Old Dominion University",  "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Virginia Tech",            "min_gpa": 3.2, "notes": "Higher bar; competitive majors may require more."},
    {"school": "Radford University",       "min_gpa": 2.5, "notes": "Minimum threshold."},
    {"school": "Christopher Newport",      "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "UVA",                      "min_gpa": None, "notes": "NOT covered by VCCS GAA."},
]

# LCPS official grading scale (Stone Bridge HS / Loudoun County)
def score_to_letter_and_gpa(score):
    """Full LCPS scale — used for GPA calculations across all years."""
    if score >= 98: return "A+", 4.0
    if score >= 93: return "A",  4.0
    if score >= 90: return "A-", 3.7
    if score >= 87: return "B+", 3.3
    if score >= 83: return "B",  3.0
    if score >= 80: return "B-", 2.7
    if score >= 77: return "C+", 2.3
    if score >= 73: return "C",  2.0
    if score >= 70: return "C-", 1.7
    if score >= 67: return "D+", 1.3
    if score >= 63: return "D",  1.0
    if score >= 60: return "D-", 0.7
    return "F", 0.0


def get_grade_info(score):
    """Reward system — returns letter, earnings, and GPA points."""
    letter, gpa_pts = score_to_letter_and_gpa(score)
    earnings = rates.get(letter, 0.0)
    return letter, earnings, gpa_pts


def row_color(score, missing):
    if missing > 0: return '#d3d3d3'
    if score >= 90: return '#d4edda'
    if score >= 80: return '#cce5ff'
    if score >= 70: return '#fff3cd'
    return '#ffe0e0'


st.markdown(
    "<style>.stMetric { border-left: 5px solid #800000; } h1 { color: #000080; }</style>",
    unsafe_allow_html=True,
)


# --- 2. DATA ENGINE ---
def load_data():
    path = Path(__file__).parent.parent / "data" / "grades.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return pd.DataFrame(json.load(f))
    except Exception:
        return None


def load_history():
    path = Path(__file__).parent.parent / "data" / "grade_history.json"
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def compute_cumulative_gpa(history, weighted=False):
    total_pts = 0.0
    total_cred = 0.0
    for year in history:
        for c in year.get("courses", []):
            score = c.get("score", 0)
            if score == 0:
                continue
            credits = c.get("credits", 1.0)
            _, pts = score_to_letter_and_gpa(score)
            if weighted and c.get("honors", False):
                pts = min(pts + 0.5, 5.0)
            total_pts += pts * credits
            total_cred += credits
    if total_cred == 0:
        return None, 0
    return round(total_pts / total_cred, 3), total_cred


def compute_year_gpa(courses, weighted=False):
    total_pts = 0.0
    total_cred = 0.0
    for c in courses:
        score = c.get("score", 0)
        if score == 0:
            continue
        credits = c.get("credits", 1.0)
        _, pts = score_to_letter_and_gpa(score)
        if weighted and c.get("honors", False):
            pts = min(pts + 0.5, 5.0)
        total_pts += pts * credits
        total_cred += credits
    if total_cred == 0:
        return None
    return round(total_pts / total_cred, 3)


# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df = load_data()
history = load_history()
cum_gpa_uw, total_credits = compute_cumulative_gpa(history, weighted=False)
cum_gpa_w,  _             = compute_cumulative_gpa(history, weighted=True)

st.title(f"\U0001f393 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    if 'missing' not in current_df.columns:
        current_df['missing'] = 0

    # ── Sidebar: Motivation Simulator ───────────────────────────────────────
    st.sidebar.header("\U0001f680 Motivation Simulator")
    st.sidebar.caption("Drag a slider to see how improving each class changes your earnings:")
    boosts = {}
    for _, row in current_df.iterrows():
        label = row['subject'][:24] + ('…' if len(row['subject']) > 24 else '')
        boosts[row['subject']] = st.sidebar.slider(label, 0, 15, 0, key=f"boost_{row['subject']}")
    st.sidebar.markdown("---")
    st.sidebar.warning("\U0001f9b7 **Reminder**: Ben, put the bands on your braces!")

    current_df['boost'] = current_df['subject'].map(boosts)
    current_df['Display Score'] = (current_df['score'] + current_df['boost']).clip(upper=100)
    grade_data = current_df['Display Score'].apply(get_grade_info)
    current_df['Grade'], current_df['Earnings'], current_df['Points'] = zip(*grade_data)

    # ── Summary metrics ──────────────────────────────────────────────────────
    avg_score   = current_df['score'].mean()
    _, _, gpa_v = get_grade_info(avg_score)

    has_all_years = all(year.get("courses") for year in history)
    gpa_label = "Cumul. GPA (UW)" if cum_gpa_uw else "Cumul. GPA"

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Earnings",   f"${current_df['Earnings'].sum():,.2f}")
    m2.metric("Max Potential",      "$1,000.00")
    m3.metric("11th Grade GPA",     f"{gpa_v:.2f}")
    if cum_gpa_uw:
        delta_color = "normal" if cum_gpa_uw >= GMU_THRESHOLD else "inverse"
        m4.metric(gpa_label,        f"{cum_gpa_uw:.3f}",
                  delta=f"{'✅' if cum_gpa_uw >= GMU_THRESHOLD else '⚠️'} GMU needs {GMU_THRESHOLD}")
        m5.metric("Cumul. GPA (W)", f"{cum_gpa_w:.3f}",
                  help="Weighted: Honors +0.5, AP +1.0")
    else:
        m4.metric("Cumul. GPA", "Needs 9th grade →")
        m5.metric("GMU Target", f"{GMU_THRESHOLD}")

    # ── Reward Breakdown — 11th Grade ────────────────────────────────────────
    st.subheader("\U0001f4b0 Reward Breakdown — 11th Grade Final")
    key_items = [
        ('#d4edda', 'A &nbsp;(90+)'), ('#cce5ff', 'B &nbsp;(80–89)'),
        ('#fff3cd', 'C &nbsp;(70–79)'), ('#ffe0e0', 'D / F &nbsp;(&lt;70)'),
        ('#d3d3d3', '⚠️&nbsp; Missing Work'),
    ]
    key_cols = st.columns(len(key_items))
    for col, (bg, label) in zip(key_cols, key_items):
        col.markdown(
            f'<div style="background:{bg};padding:6px 10px;border-radius:4px;'
            f'text-align:center;font-size:0.82em;border:1px solid #bbb">{label}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    missing_vals   = current_df['missing'].values
    display_scores = current_df['Display Score'].values
    display_df     = current_df[['subject', 'Display Score', 'Grade', 'Earnings']]

    def highlight_row(row):
        color = row_color(display_scores[row.name], missing_vals[row.name])
        return [f'background-color: {color}'] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_row, axis=1).format({"Earnings": "${:,.2f}"}),
        hide_index=True,
    )
    st.markdown("---")

    # ── Grade History & Cumulative GPA ───────────────────────────────────────
    st.header("\U0001f4ca Grade History & Cumulative GPA")

    for year_data in history:
        courses = year_data.get("courses", [])
        label   = year_data["label"]
        note    = year_data.get("note", "")

        if not courses:
            st.subheader(f"{label} — *grades not yet entered*")
            if note:
                st.caption(f"📋 {note}")
            continue

        yr_gpa_uw = compute_year_gpa(courses, weighted=False)
        yr_gpa_w  = compute_year_gpa(courses, weighted=True)
        gpa_str   = f"UW: {yr_gpa_uw:.3f}  |  W: {yr_gpa_w:.3f}" if yr_gpa_uw else "—"
        st.subheader(f"{label} — GPA {gpa_str}")

        rows = []
        for c in courses:
            score = c.get("score", 0)
            if score == 0:
                continue
            letter, pts = score_to_letter_and_gpa(score)
            w_pts = min(pts + 0.5, 5.0) if c.get("honors") else pts
            rows.append({
                "Subject":    c["subject"],
                "Score":      c["note"] if c.get("note") else score,
                "Grade":      letter,
                "Credits":    c.get("credits", 1.0),
                "GPA (UW)":   pts,
                "GPA (W)":    w_pts,
                "Honors":     "H" if c.get("honors") else "",
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df.style.format({"GPA (UW)": "{:.1f}", "GPA (W)": "{:.1f}"}),
                         hide_index=True)

    st.markdown("---")
    if cum_gpa_uw:
        gmu_gap = GMU_THRESHOLD - cum_gpa_uw
        if gmu_gap <= 0:
            st.success(f"✅ **Cumulative GPA (Unweighted): {cum_gpa_uw:.3f}** — Meets GMU {GMU_THRESHOLD} guaranteed admission threshold!")
        else:
            st.warning(
                f"⚠️ **Cumulative GPA (Unweighted): {cum_gpa_uw:.3f}** — "
                f"**{gmu_gap:.3f} points below GMU {GMU_THRESHOLD} threshold.** "
                f"Senior year is critical."
            )
        st.info(f"Weighted GPA (Honors/AP boost): **{cum_gpa_w:.3f}** across {total_credits:.1f} credits")
        if not all(year.get("courses") for year in history):
            st.caption("⚠️ 9th grade grades not yet entered — cumulative GPA above is 10th + 11th only. "
                       "Add from ParentVue Documents → Year End Report Card (06/24/2024).")
    else:
        st.info("Add 9th grade scores to `data/grade_history.json` to compute cumulative GPA.")

    st.markdown("---")

    # ── GMU Guaranteed Admission ─────────────────────────────────────────────
    st.header("\U0001f3eb GMU Guaranteed Admission — Direct Freshman Path")
    st.markdown(
        f"**George Mason University guarantees freshman admission to Virginia HS students "
        f"with a cumulative GPA ≥ {GMU_THRESHOLD} by end of junior year.** "
        f"Ben just finished junior year — this window has closed for evaluation. "
        f"The cumulative GPA he carries into senior year IS his qualifying GPA."
    )

    if cum_gpa_uw:
        gap = GMU_THRESHOLD - cum_gpa_uw
        if gap <= 0:
            st.success(f"✅ **Ben qualifies: {cum_gpa_uw:.3f} ≥ {GMU_THRESHOLD}**")
        else:
            st.error(
                f"❌ **Ben does not yet qualify: {cum_gpa_uw:.3f} vs. {GMU_THRESHOLD} needed "
                f"(gap: {gap:.3f})**\n\n"
                f"Note: this calculation uses 10th + 11th grade only. 9th grade data may change this."
            )

    st.markdown("---")

    # ── VCCS Fallback Path ───────────────────────────────────────────────────
    st.header("\U0001f4cb VCCS Guaranteed Admission — Fallback via NOVA")
    st.caption(
        "If Ben doesn't hit the GMU direct-admission threshold, he can enroll at NOVA "
        "(Northern Virginia Community College — cheaper, closer) → complete AA/AS → "
        "transfer to a Virginia 4-year school with guaranteed admission. "
        "The GPA requirement below applies to credits earned AT NOVA, not HS GPA."
    )

    gaa_rows = []
    for s in VCCS_SCHOOLS:
        if s["min_gpa"] is None:
            req, status = "N/A", "❌ Not available"
        else:
            req    = f"{s['min_gpa']:.1f}"
            status = "✅ Achievable" if s["min_gpa"] <= 3.2 else "⚠️ Competitive"
        gaa_rows.append({"School": s["school"], "Min GPA at NOVA": req,
                         "Status": status, "Notes": s["notes"]})
    st.dataframe(pd.DataFrame(gaa_rows), hide_index=True, use_container_width=True)
    st.caption(
        "Virginia Tech requires 3.2+ and is the hardest bar. GMU via VCCS needs only 3.0 at NOVA — "
        "easier bar than the direct HS admission threshold, and NOVA credits are cheap."
    )

    st.markdown("---")

    # ── Certification Payouts ────────────────────────────────────────────────
    st.header("\U0001f3c6 Certification Payouts")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("CCNA Bonus")
        st.metric("Potential", "$1,000.00")
        st.progress(0.1, text="Coursework Started")
    with c2:
        st.subheader("Security+ Bonus")
        st.metric("Potential", "$1,000.00")
        st.progress(0.0, text="Queued")

else:
    st.info("Syncing grades from ParentVUE email...")
