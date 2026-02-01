import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- 1. CONFIGURATION LAYER (Pulled from Azure Env Vars) ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Student") 
RATE_APLUS = float(os.getenv("RATE_APLUS", 150.0))
RATE_A = float(os.getenv("RATE_A", 125.0))
RATE_AMINUS = float(os.getenv("RATE_AMINUS", 100.0))
RATE_BPLUS = float(os.getenv("RATE_BPLUS", 75.0))
RATE_B = float(os.getenv("RATE_B", 50.0))
RATE_BMINUS = float(os.getenv("RATE_BMINUS", 25.0))

rates = {
    "A+": RATE_APLUS, "A": RATE_A, "A-": RATE_AMINUS, 
    "B+": RATE_BPLUS, "B": RATE_B, "B-": RATE_BMINUS
}

def get_payout(score):
    if score >= 97: return rates["A+"]
    if score >= 93: return rates["A"]
    if score >= 90: return rates["A-"]
    if score >= 87: return rates["B+"]
    if score >= 83: return rates["B"]
    if score >= 80: return rates["B-"]
    return 0

# --- 2. DATA LAYER (Storage Sync) ---
def get_data_and_history():
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connect_str:
        st.error("Storage Connection String missing!")
        return None, pd.DataFrame()

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client("dean-family-grades")
    
    historical_data = []
    # Sort blobs to find the newest one
    blobs = sorted(container_client.list_blobs(), key=lambda x: x.name)
    
    current_json = None
    for blob in blobs:
        if blob.name.startswith("grades_") and blob.name.endswith(".json"):
            content = container_client.download_blob(blob.name).readall()
            df = pd.read_json(io.BytesIO(content))
            # Extract date for history chart
            date_val = blob.name.split('_')[1].replace('.json', '')
            df['ReportDate'] = pd.to_datetime(date_val)
            historical_data.append(df)
            current_json = df # Last one in loop is newest

    return current_json, (pd.concat(historical_data) if historical_data else pd.DataFrame())

# --- 3. DASHBOARD UI ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df, history_df = get_data_and_history()

# Header Section
st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if not history_df.empty and len(history_df['ReportDate'].unique()) >= 2:
    # Summary Table logic
    dates = sorted(history_df['ReportDate'].unique())
    latest_avg = history_df[history_df['ReportDate'] == dates[-1]]['grade_numeric'].mean()
    prev_avg = history_df[history_df['ReportDate'] == dates[-2]]['grade_numeric'].mean()
    delta = latest_avg - prev_avg
    
    st.subheader("📊 Weekly Progress Summary")
    st.metric("Academic Performance", f"{latest_avg:.1f}%", delta=f"{delta:.1f}%")

# Main Stats Logic
if current_df is not None:
    # Convert dataframe to a dict for the simulator
    current_data = dict(zip(current_df['subject'], current_df['score']))
    missing_assignments = int(current_df['missing'].iloc[0]) if 'missing' in current_df else 0
else:
    # Fallback to empty state
    current_data = {'Subject': 0}
    missing_assignments = 0

current_total = sum(get_payout(s) for s in current_data.values())
max_payout = len(current_data) * rates["A+"]

# Metrics Row
m1, m2, m3 = st.columns(3)
with m1: st.metric("Max Potential", f"${max_payout:.2f}")
with m2: 
    val = f"${current_total:.2f}" if missing_assignments == 0 else "$0.00"
    st.metric("Current Earned", val, delta=f"- ${current_total} Locked" if missing_assignments > 0 else None, delta_color="inverse")
with m3:
    st.metric("Simulation Value", f"${current_total:.2f}")

# Alert Box
if missing_assignments > 0:
    st.error(f"🛑 PAYOUT IS LOCKED. You have {missing_assignments} missing assignments! Turn them in to unlock your ${current_total}!")

# Charts
if not history_df.empty:
    st.divider()
    st.header("📈 Performance Over Time")
    st.line_chart(history_df.set_index('ReportDate')['grade_numeric'])
