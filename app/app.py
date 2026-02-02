import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- 1. CONFIGURATION ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Ben Dean") 
rates = {
    "A+": float(os.getenv("RATE_APLUS", 150.0)),
    "A": float(os.getenv("RATE_A", 125.0)),
    "A-": float(os.getenv("RATE_AMINUS", 100.0)),
    "B+": float(os.getenv("RATE_BPLUS", 75.0)),
    "B": float(os.getenv("RATE_B", 50.0)),
    "B-": float(os.getenv("RATE_BMINUS", 25.0))
}

# Helper to get letter and payout
def get_grade_info(score):
    if score >= 97: return "A+", rates["A+"]
    if score >= 93: return "A", rates["A"]
    if score >= 90: return "A-", rates["A-"]
    if score >= 87: return "B+", rates["B+"]
    if score >= 83: return "B", rates["B"]
    if score >= 80: return "B-", rates["B-"]
    return "C or below", 0.0

# School Colors
st.markdown(f"<style>.stMetric {{ border-left: 5px solid #800000; }} h1 {{ color: #000080; }}</style>", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        st.error("DEBUG: AZURE_STORAGE_CONNECTION_STRING is missing!")
        return None
    
    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        container = client.get_container_client("dean-family-grades")
        blobs = list(container.list_blobs())
        
        if not blobs:
            st.warning("DEBUG: Container is EMPTY.")
            return None

        # Get latest blob only for the main dashboard
        latest_blob = sorted(blobs, key=lambda x: x.name)[-1]
        data = container.download_blob(latest_blob.name).readall()
        return pd.read_json(io.BytesIO(data))
    except Exception as e:
        st.error(f"DEBUG: Storage Connection Failed: {str(e)}")
        return None

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df = load_data()

st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    # --- WHAT-IF SLIDER ---
    st.sidebar.header("🚀 What-If Analysis")
    st.sidebar.write("See how much more you'd make by bumping your scores!")
    score_boost = st.sidebar.slider("Add points to all classes:", 0, 15, 0)
    
    # Calculate Simulated Data
    current_df['Display Score'] = (current_df['score'] + score_boost).clip(upper=100)
    
    # Apply logic to get Letter and Payout
    grade_data = current_df['Display Score'].apply(get_grade_info)
    current_df['Grade'] = [x[0] for x in grade_data]
    current_df['Earnings'] = [x[1] for x in grade_data]
    
    # Calculate Totals
    base_total = current_df['Earnings'].sum()
    all_as = all(s >= 90 for s in current_df['Display Score'])
    bonus = 100.0 if all_as else 0.0
    current_total = base_total + bonus
    
    # Metrics
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Max Potential", "$1,000.00")
    with m2: 
        label = "Projected Payout" if score_boost > 0 else "Earned To Date"
        st.metric(label, f"${current_total:,.2f}")
    with m3: st.metric("GPA (Current)", f"{current_df['score'].mean():.1f}%")

    if all_as and score_boost > 0:
        st.sidebar.success("🎉 Simulated Straight-A Bonus included!")

    st.subheader("💰 Reward Breakdown")
    
    # Format for display
    display_df = current_df[['subject', 'Display Score', 'Grade', 'Earnings']].copy()
    display_df.columns = ['Subject', 'Score', 'Grade', 'Earnings']
    
    # Currency formatting
    st.dataframe(
        display_df.style.format({"Earnings": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Waiting for first grade update...")

# --- BACKLOG REMINDERS (FOOTER) ---
st.markdown("---")
st.caption("Next Milestone: SMS Failure Alerts | Inflation Escalator | Braces Reminder")
