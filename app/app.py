import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

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

st.markdown(f"<style>.stMetric {{ border-left: 5px solid #800000; }} h1 {{ color: #000080; }}</style>", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str: return None
    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        container = client.get_container_client("dean-family-grades")
        data = container.download_blob("grades.json").readall()
        return pd.read_json(io.BytesIO(data))
    except: return None

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df = load_data()
st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    # Sidebar
    st.sidebar.header("🚀 Motivation Simulator")
    boost = st.sidebar.slider("Simulate score boost:", 0, 15, 0)
    st.sidebar.markdown("---")
    st.sidebar.warning("🦷 **Reminder**: Ben, put the bands on your braces!")

    current_df['Display Score'] = (current_df['score'] + boost).clip(upper=100)
    grade_data = current_df['Display Score'].apply(get_grade_info)
    current_df['Grade'], current_df['Earnings'], current_df['Points'] = zip(*grade_data)

    # Metrics
    avg_score = current_df['score'].mean()
    overall_letter, _, gpa_val = get_grade_info(avg_score)
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Earnings", f"${current_df['Earnings'].sum():,.2f}")
    m2.metric("Max Potential", "$1,000.00")
    m3.metric("GPA Status", f"{avg_score:.1f}% ({gpa_val:.1f} / {overall_letter})")

    st.subheader("💰 Reward Breakdown")
    st.dataframe(current_df[['subject', 'Display Score', 'Grade', 'Earnings']].style.format({"Earnings": "${:,.2f}"}), hide_index=True)

    # Certification Bonuses
    st.markdown("---")
    st.header("🏆 Certification Payouts")
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
