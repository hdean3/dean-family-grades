import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path

# --- 1. CONFIGURATION ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Ben Dean")
rates = {
    "A+": 150.0, "A": 125.0, "A-": 100.0,
    "B+": 75.0, "B": 50.0, "B-": 25.0
}

VCCS_SCHOOLS = [
    {"school": "George Mason University",   "min_gpa": 3.0, "notes": "Most programs. Ideal — right in NOVA."},
    {"school": "James Madison University",  "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Virginia Commonwealth",     "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Old Dominion University",   "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "Virginia Tech",             "min_gpa": 3.2, "notes": "Higher bar; competitive majors may require more."},
    {"school": "Radford University",        "min_gpa": 2.5, "notes": "Minimum threshold."},
    {"school": "Christopher Newport",       "min_gpa": 3.0, "notes": "Most programs."},
    {"school": "UVA",                       "min_gpa": None, "notes": "NOT covered by VCCS GAA."},
]


def get_grade_info(score):
    if score >= 97: return "A+", rates["A+"], 4.0
    if score >= 93: return "A",  rates["A"],  4.0
    if score >= 90: return "A-", rates["A-"], 3.7
    if score >= 87: return "B+", rates["B+"], 3.3
    if score >= 83: return "B",  rates["B"],  3.0
    if score >= 80: return "B-", rates["B-"], 2.7
    return "C or below", 0.0, 2.0


def score_to_gpa_points(score):
    _, _, pts = get_grade_info(score)
    return pts


def row_color(score, missing):
    if missing > 0:   return '#d3d3d3'
    if score >= 90:   return '#d4edda'
    if score >= 80:   return '#cce5ff'
    if score >= 70:   return '#fff3cd'
    return '#ffe0e0'


st.markdown(
    "<style>.stMetric { border-left: 5px solid #800000; } h1 { color: #000080; }</style>",
    unsafe_allow_html=True,
)


# --- 2. DATA ENGINE ---
def load_data():
    grades_path = Path(__file__).parent.parent / "data" / "grades.json"
    if not grades_path.exists():
        return None
    try:
        with open(grades_path) as f:
            data = json.load(f)
        return pd.DataFrame(data)
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


def compute_cumulative_gpa(history):
    total_points = 0.0
    total_credits = 0.0
    for year in history:
        for course in year["courses"]:
            score = course.get("score", 0)
            credits = course.get("credits", 1.0)
            if score == 0:
                continue  # skip placeholder / unfilled entries
            pts = score_to_gpa_points(score)
            total_points += pts * credits
            total_credits += credits
    if total_credits == 0:
        return None, 0
    return round(total_points / total_credits, 2), total_credits


# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df = load_data()
history = load_history()
cumulative_gpa, total_credits = compute_cumulative_gpa(history)

st.title(f"\U0001f393 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    if 'missing' not in current_df.columns:
        current_df['missing'] = 0

    # ── Per-class Motivation Simulator ──────────────────────────────────────
    st.sidebar.header("\U0001f680 Motivation Simulator")
    st.sidebar.caption("Drag a slider to see how improving each class changes your earnings:")
    boosts = {}
    for _, row in current_df.iterrows():
        label = row['subject'][:24] + ('…' if len(row['subject']) > 24 else '')
        boosts[row['subject']] = st.sidebar.slider(
            label, 0, 15, 0, key=f"boost_{row['subject']}"
        )
    st.sidebar.markdown("---")
    st.sidebar.warning("\U0001f9b7 **Reminder**: Ben, put the bands on your braces!")

    current_df['boost'] = current_df['subject'].map(boosts)
    current_df['Display Score'] = (current_df['score'] + current_df['boost']).clip(upper=100)
    grade_data = current_df['Display Score'].apply(get_grade_info)
    current_df['Grade'], current_df['Earnings'], current_df['Points'] = zip(*grade_data)

    # ── Summary metrics ──────────────────────────────────────────────────────
    avg_score = current_df['score'].mean()
    overall_letter, _, gpa_val = get_grade_info(avg_score)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Earnings", f"${current_df['Earnings'].sum():,.2f}")
    m2.metric("Max Potential", "$1,000.00")
    m3.metric("This Semester GPA", f"{gpa_val:.2f} / {overall_letter}")
    if cumulative_gpa is not None:
        m4.metric("Cumulative GPA", f"{cumulative_gpa:.2f}", help=f"Weighted across {total_credits:.0f} credits")
    else:
        m4.metric("Cumulative GPA", "Enter prior grades →", help="Add 9th/10th grade scores to grade_history.json")

    # ── Reward Breakdown table ───────────────────────────────────────────────
    st.subheader("\U0001f4b0 Reward Breakdown — 11th Grade Final")

    key_items = [
        ('#d4edda', 'A &nbsp;(90+)'),
        ('#cce5ff', 'B &nbsp;(80–89)'),
        ('#fff3cd', 'C &nbsp;(70–79)'),
        ('#ffe0e0', 'D / F &nbsp;(&lt;70)'),
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

    missing_vals = current_df['missing'].values
    display_scores = current_df['Display Score'].values
    display_df = current_df[['subject', 'Display Score', 'Grade', 'Earnings']]

    def highlight_row(row):
        color = row_color(display_scores[row.name], missing_vals[row.name])
        return [f'background-color: {color}'] * len(row)

    st.dataframe(
        display_df.style
            .apply(highlight_row, axis=1)
            .format({"Earnings": "${:,.2f}"}),
        hide_index=True,
    )

    st.markdown("---")

    # ── Grade History & Cumulative GPA ───────────────────────────────────────
    st.header("\U0001f4ca Grade History & Cumulative GPA")

    if history:
        for year_data in history:
            has_real_grades = any(c.get("score", 0) > 0 for c in year_data["courses"])
            label = year_data["label"]
            if not has_real_grades:
                st.subheader(f"{label} *(grades not yet entered)*")
                st.caption("Add scores to `data/grade_history.json` to include this year in cumulative GPA.")
                continue

            courses = year_data["courses"]
            rows = []
            for c in courses:
                if c.get("score", 0) == 0:
                    continue
                letter, _, pts = get_grade_info(c["score"])
                rows.append({
                    "Subject": c["subject"],
                    "Score": c["score"],
                    "Grade": letter,
                    "GPA Pts": pts,
                    "Credits": c.get("credits", 1.0),
                })
            if not rows:
                continue
            year_df = pd.DataFrame(rows)
            weighted = (year_df["GPA Pts"] * year_df["Credits"]).sum() / year_df["Credits"].sum()
            st.subheader(f"{label} — GPA: {weighted:.2f}")
            st.dataframe(year_df[["Subject", "Score", "Grade", "GPA Pts"]].style.format({"GPA Pts": "{:.1f}"}), hide_index=True)

        if cumulative_gpa is not None:
            st.success(f"**Cumulative GPA (all years with data): {cumulative_gpa:.2f}** across {total_credits:.0f} credits")
        else:
            st.info("No historical grade data yet. Fill in 9th and 10th grade scores in `data/grade_history.json`.")
    else:
        st.info("No grade history file found.")

    st.markdown("---")

    # ── VCCS Guaranteed Admission Agreement ─────────────────────────────────
    st.header("\U0001f3eb VCCS Guaranteed Admission Agreement")
    st.caption(
        "If Ben earns an Associate's degree at NOVA (or any Virginia community college) "
        "with the required GPA, he is **guaranteed transfer admission** to these Virginia universities."
    )

    if cumulative_gpa is not None:
        current_gpa_display = cumulative_gpa
        gpa_label = "Cumulative HS GPA"
    else:
        current_gpa_display = gpa_val
        gpa_label = "This Semester GPA (cumulative not yet available)"

    st.info(f"**{gpa_label}: {current_gpa_display:.2f}** — this is for reference. "
            f"The GAA GPA requirement applies to credits earned **at NOVA**, not HS GPA.")

    gaa_rows = []
    for s in VCCS_SCHOOLS:
        if s["min_gpa"] is None:
            status = "❌ Not available"
            req = "N/A"
        else:
            req = f"{s['min_gpa']:.1f}"
            # Show what GPA at NOVA Ben would need — HS GPA is informational only
            status = "✅ Achievable" if s["min_gpa"] <= 3.5 else "⚠️ Competitive"
        gaa_rows.append({
            "School": s["school"],
            "Min GPA at NOVA": req,
            "Status": status,
            "Notes": s["notes"],
        })

    gaa_df = pd.DataFrame(gaa_rows)
    st.dataframe(gaa_df, hide_index=True, use_container_width=True)

    st.caption(
        "**How it works:** Ben enrolls at NOVA after graduation → earns Associate's degree "
        "(typically 60 credits / 2 years) → maintains required GPA → guaranteed admission to chosen school. "
        "45+ credits with the right GPA can trigger the guarantee even before completing the full AA/AS at some schools. "
        "Virginia Tech requires 3.2+ and is the hardest bar. GMU is the most practical given location."
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
