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

st.markdown("<style>.stMetric { border-left: 5px solid #800000; } h1 { color: #000080; }</style>",
            unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    # Read grades.json from repo (data/ directory, relative to project root)
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
    st.sidebar.header("\U0001f680 Motivation Simulator")
    boost = st.sidebar.slider("Simulate score boost:", 0, 15, 0)
    st.sidebar.markdown("---")
    st.sidebar.warning("\U0001f9b7 **Reminder**: Ben, put the bands on your braces!")

    current_df['Display Score'] = (current_df['score'] + boost).clip(upper=100)
    grade_data = current_df['Display Score'].apply(get_grade_info)
    current_df['Grade'], current_df['Earnings'], current_df['Points'] = zip(*grade_data)

    avg_score = current_df['score'].mean()
    overall_letter, _, gpa_val = get_grade_info(avg_score)
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Earnings", f"${current_df['Earnings'].sum():,.2f}")
    m2.metric("Max Potential", "$1,000.00")
    m3.metric("GPA Status", f"{avg_score:.1f}% ({gpa_val:.1f} / {overall_letter})")

    st.subheader("\U0001f4b0 Reward Breakdown")
    # Ensure missing column exists (graceful fallback for old grades.json)
    if 'missing' not in current_df.columns:
        current_df['missing'] = 0

    # missing_vals drives row highlight; it is NOT included in the display columns
    missing_vals = current_df['missing'].values
    display_df = current_df[['subject', 'Display Score', 'Grade', 'Earnings']]

    def highlight_missing(row):
        color = 'background-color: #ffe0e0' if missing_vals[row.name] > 0 else ''
        return [color] * len(row)

    st.dataframe(
        display_df.style
            .apply(highlight_missing, axis=1)
            .format({"Earnings": "${:,.2f}"}),
        hide_index=True
    )

    st.markdown("---")
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
