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


def get_grade_info(score):
    if score >= 97: return "A+", rates["A+"], 4.0
    if score >= 93: return "A", rates["A"], 4.0
    if score >= 90: return "A-", rates["A-"], 3.7
    if score >= 87: return "B+", rates["B+"], 3.3
    if score >= 83: return "B", rates["B"], 3.0
    if score >= 80: return "B-", rates["B-"], 2.7
    return "C or below", 0.0, 2.0


def row_color(score, missing):
    """Return background hex based on grade band; missing work overrides."""
    if missing > 0:
        return '#d3d3d3'   # grey   — missing assignments
    if score >= 90:
        return '#d4edda'   # green  — A
    if score >= 80:
        return '#cce5ff'   # blue   — B
    if score >= 70:
        return '#fff3cd'   # yellow — C
    return '#ffe0e0'       # red    — D / F


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


# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df = load_data()
st.title(f"\U0001f393 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    # Graceful fallback if grades.json predates missing-assignments field
    if 'missing' not in current_df.columns:
        current_df['missing'] = 0

    # ── Per-class Motivation Simulator ──────────────────────────────────────
    st.sidebar.header("\U0001f680 Motivation Simulator")
    st.sidebar.caption("Drag a slider to see how improving each class changes your earnings:")
    boosts = {}
    for _, row in current_df.iterrows():
        label = row['subject'][:24] + ('\u2026' if len(row['subject']) > 24 else '')
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
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Earnings", f"${current_df['Earnings'].sum():,.2f}")
    m2.metric("Max Potential", "$1,000.00")
    m3.metric("GPA Status", f"{avg_score:.1f}% ({gpa_val:.1f} / {overall_letter})")

    # ── Reward Breakdown table ───────────────────────────────────────────────
    st.subheader("\U0001f4b0 Reward Breakdown")

    # Color legend
    key_items = [
        ('#d4edda', 'A &nbsp;(90+)'),
        ('#cce5ff', 'B &nbsp;(80–89)'),
        ('#fff3cd', 'C &nbsp;(70–79)'),
        ('#ffe0e0', 'D / F &nbsp;(&lt;70)'),
        ('#d3d3d3', '\u26a0\ufe0f&nbsp; Missing Work'),
    ]
    key_cols = st.columns(len(key_items))
    for col, (bg, label) in zip(key_cols, key_items):
        col.markdown(
            f'<div style="background:{bg};padding:6px 10px;border-radius:4px;'
            f'text-align:center;font-size:0.82em;border:1px solid #bbb">{label}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # Styled dataframe — color driven by display score + missing flag
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
