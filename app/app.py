import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- 1. CONFIGURATION & THEME ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Student") 
rates = {
    "A+": float(os.getenv("RATE_APLUS", 150.0)),
    "A": float(os.getenv("RATE_A", 125.0)),
    "A-": float(os.getenv("RATE_AMINUS", 100.0)),
    "B+": float(os.getenv("RATE_BPLUS", 75.0)),
    "B": float(os.getenv("RATE_B", 50.0)),
    "B-": float(os.getenv("RATE_BMINUS", 25.0))
}

# School Colors (Customize these hex codes!)
PRIMARY_COLOR = "#1B365D" # Deep Navy
SECONDARY_COLOR = "#FFC72C" # Gold

st.markdown(f"""
    <style>
    .main {{ background-color: #f5f7f9; }}
    .stMetric {{ border: 2px solid {PRIMARY_COLOR}; padding: 15px; border-radius: 10px; background-color: white; }}
    h1, h2, h3 {{ color: {PRIMARY_COLOR}; }}
    </style>
    """, unsafe_allow_root=True)

def get_payout(score):
    if score >= 97: return rates["A+"]
    if score >= 93: return rates["A"]
    if score >= 90: return rates["A-"]
    if score >= 87: return rates["B+"]
    if score >= 83: return rates["B"]
    if score >= 80: return rates["B-"]
    return 0

# --- 2. PROACTIVE DATA SYNC ---
def load_data():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str or "DefaultEndpoints" not in conn_str:
        st.error("Invalid Storage Connection String!")
        return None, pd.DataFrame()

    client = BlobServiceClient.from_connection_string(conn_str)
    container = client.get_container_client("dean-family-grades")
    blobs = sorted(container.list_blobs(), key=lambda x: x.name)
    
    historical_data = []
    latest_df = None
    for blob in blobs:
        if blob.name.startswith("grades_"):
            data = container.download_blob(blob.name).readall()
            df = pd.read_json(io.BytesIO(data))
            date_str = blob.name.split('_')[1].replace('.json', '')
            df['ReportDate'] = pd.to_datetime(date_str)
            historical_data.append(df)
            latest_df = df 

    return latest_df, (pd.concat(historical_data) if historical_data else pd.DataFrame())

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df, history_df = load_data()

st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    # Calculate Payouts per class
    current_df['Earnings'] = current_df['score'].apply(get_payout)
    current_total = current_df['Earnings'].sum()
    missing_count = int(current_df['missing'].iloc[0]) if 'missing' in current_df.columns else 0
    
    # TOP METRICS
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Max Potential", f"${len(current_df)*rates['A+']:.2f}")
    with m2: st.metric("Earned To Date", f"${current_total:.2f}" if missing_count == 0 else "$0.00", 
                       delta=f"- ${current_total} Locked" if missing_count > 0 else None, delta_color="inverse")
    with m3: st.metric("Overall GPA", f"{current_df['score'].mean():.1f}%")

    # NEW: INDIVIDUAL CLASS BREAKDOWN
    st.subheader("💰 Reward Breakdown by Class")
    breakdown_cols = st.columns(len(current_df))
    for i, row in current_df.iterrows():
        with breakdown_cols[i]:
            st.metric(row['subject'], f"${row['Earnings']:.0f}", help=f"Score: {row['score']}%")

    if missing_count > 0:
        st.error(f"🛑 PAYOUT IS LOCKED: {missing_count} missing assignment(s) detected.")

if not history_df.empty:
    st.divider()
    st.header("📈 Grade Performance Over Time")
    st.line_chart(history_df.groupby('ReportDate')['score'].mean())
