import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- 1. PRIVACY & PAYOUT CONFIGURATION ---
# These pull from Azure Env Vars. Hardcoded defaults are for the Public Repo.
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

# --- 2. DATA LAYER ---
def get_dashboard_data():
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connect_str:
        return None, pd.DataFrame()

    client = BlobServiceClient.from_connection_string(connect_str)
    container = client.get_container_client("dean-family-grades")
    
    historical_data = []
    blobs = sorted(container.list_blobs(), key=lambda x: x.name)
    
    latest_df = None
    for blob in blobs:
        if blob.name.startswith("grades_") and blob.name.endswith(".json"):
            data = container.download_blob(blob.name).readall()
            df = pd.read_json(io.BytesIO(data))
            # Tag the date from filename: grades_2026-02-01.json
            date_str = blob.name.split('_')[1].replace('.json', '')
            df['ReportDate'] = pd.to_datetime(date_str)
            historical_data.append(df)
            latest_df = df 

    return latest_df, (pd.concat(historical_data) if historical_data else pd.DataFrame())

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df, history_df = get_dashboard_data()

st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

# Metric Summary at the top
if not history_df.empty and len(history_df['ReportDate'].unique()) >= 2:
    dates = sorted(history_df['ReportDate'].unique())
    latest_avg = history_df[history_df['ReportDate'] == dates[-1]]['score'].mean()
    prev_avg = history_df[history_df['ReportDate'] == dates[-2]]['score'].mean()
    delta = latest_avg - prev_avg
    st.subheader("📊 Weekly Progress Summary")
    st.metric("Overall Performance", f"{latest_avg:.1f}%", delta=f"{delta:.1f}%")

# Metrics & Payouts
if current_df is not None:
    # Build dict from 'subject' and 'score' columns
    current_data = dict(zip(current_df['subject'], current_df['score']))
    # Look for 'missing' column in your Logic App output
    missing_count = int(current_df['missing'].iloc[0]) if 'missing' in current_df.columns else 0
else:
    current_data = {}; missing_count = 0

current_total = sum(get_payout(s) for s in current_data.values())
max_payout = len(current_data) * rates["A+"]

m1, m2, m3 = st.columns(3)
with m1: st.metric("Max Potential", f"${max_payout:.2f}")
with m2: 
    disp_val = f"${current_total:.2f}" if missing_count == 0 else "$0.00"
    st.metric("Current Earned", disp_val, delta=f"- ${current_total} Locked" if missing_count > 0 else None, delta_color="inverse")
with m3:
    st.metric("Simulated Reward", f"${current_total:.2f}")

# DYNAMIC MISSING ASSIGNMENT ALERT
if missing_count > 0:
    st.error(f"🛑 PAYOUT IS LOCKED. You have {missing_count} missing assignment(s). Turn them in to unlock your ${current_total:.2f}!")

# Trend Chart
if not history_df.empty:
    st.divider()
    st.header("📈 Grade Trends")
    st.line_chart(history_df.groupby('ReportDate')['score'].mean())
