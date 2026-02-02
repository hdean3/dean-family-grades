import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- 1. CONFIGURATION (Pulled from GitHub Actions/Azure) ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Ben Dean") 
rates = {
    "A+": float(os.getenv("RATE_APLUS", 150.0)),
    "A": float(os.getenv("RATE_A", 125.0)),
    "A-": float(os.getenv("RATE_AMINUS", 100.0)),
    "B+": float(os.getenv("RATE_BPLUS", 75.0)),
    "B": float(os.getenv("RATE_B", 50.0)),
    "B-": float(os.getenv("RATE_BMINUS", 25.0))
}

# GPA Mapping Logic
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
        blobs = list(container.list_blobs())
        if not blobs: return None
        latest_blob = sorted(blobs, key=lambda x: x.name)[-1]
        data = container.download_blob(latest_blob.name).readall()
        return pd.read_json(io.BytesIO(data))
    except: return None

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df = load_data()

st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    # --- WHAT-IF SLIDER ---
    st.sidebar.header("🚀 What-If Analysis")
    score_boost = st.sidebar.slider("Simulate a score increase:", 0, 15, 0)
    
    current_df['Display Score'] = (current_df['score'] + score_boost).clip(upper=100)
    grade_data = current_df['Display Score'].apply(get_grade_info)
    
    current_df['Grade'] = [x[0] for x in grade_data]
    current_df['Earnings'] = [x[1] for x in grade_data]
    current_df['Points'] = [x[2] for x in grade_data]
    
    total_earned = current_df['Earnings'].sum()
    avg_score = current_df['score'].mean()
    avg_gpa = current_df['Points'].mean()
    overall_letter, _, _ = get_grade_info(avg_score)

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Max Potential", "$1,000.00")
    m2.metric("Projected Payout", f"${total_earned + (100.0 if all(s >= 90 for s in current_df['Display Score']) else 0.0):,.2f}")
    m3.metric("Current GPA", f"{avg_score:.1f}% ({avg_gpa:.1f} / {overall_letter})")

    # Table
    st.subheader("💰 Reward Breakdown")
    display_df = current_df[['subject', 'Display Score', 'Grade', 'Earnings']].copy()
    display_df.columns = ['Subject', 'Score', 'Grade', 'Earnings']
    st.dataframe(display_df.style.format({"Earnings": "${:,.2f}"}), use_container_width=True, hide_index=True)
else:
    st.info("Syncing grades from ParentVUE...")
