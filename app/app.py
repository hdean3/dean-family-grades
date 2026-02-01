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

# School Colors: Maroon & Navy
st.markdown(f"""
    <style>
    .stMetric {{ border-left: 5px solid #800000; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }}
    h1, h2, h3 {{ color: #000080; font-family: 'Arial Black'; }}
    </style>
    """, unsafe_allow_html=True)

def get_payout(score):
    if score >= 97: return rates["A+"]
    if score >= 93: return rates["A"]
    if score >= 90: return rates["A-"]
    if score >= 87: return rates["B+"]
    if score >= 83: return rates["B"]
    if score >= 80: return rates["B-"]
    return 0

# --- 2. DATA ENGINE ---
def load_all_data():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str: return None, pd.DataFrame()
    client = BlobServiceClient.from_connection_string(conn_str)
    container = client.get_container_client("dean-family-grades")
    historical_data = []
    blobs = sorted(container.list_blobs(), key=lambda x: x.name)
    latest_df = None
    for blob in blobs:
        if blob.name.startswith("grades_") and blob.name.endswith(".json"):
            data = container.download_blob(blob.name).readall()
            df = pd.read_json(io.BytesIO(data))
            date_str = blob.name.split('_')[1].replace('.json', '')
            df['ReportDate'] = pd.to_datetime(date_str)
            historical_data.append(df)
            latest_df = df 
    return latest_df, (pd.concat(historical_data) if historical_data else pd.DataFrame())

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df, history_df = load_all_data()
st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    current_df['Earnings'] = current_df['score'].apply(get_payout)
    base_total = current_df['Earnings'].sum()
    
    # STRAIGHT A BONUS LOGIC ($100)
    all_as = all(score >= 90 for score in current_df['score'])
    bonus = 100.0 if all_as else 0.0
    current_total = base_total + bonus
    missing_count = int(current_df['missing'].iloc[0]) if 'missing' in current_df.columns else 0
    
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Max Potential", "$1,000.00", help="Includes $100 Straight-A Bonus")
    with m2: 
        status = f"${current_total:.2f}" if missing_count == 0 else "$0.00"
        st.metric("Earned To Date", status, delta=f"-${current_total} Locked" if missing_count > 0 else None, delta_color="inverse")
    with m3: st.metric("GPA Average", f"{current_df['score'].mean():.1f}%")

    st.subheader("💰 Individual Class Earnings")
    st.dataframe(current_df[['subject', 'score', 'Earnings']].sort_values('score', ascending=False), use_container_width=True, hide_index=True)
    
    if bonus > 0: st.success("🌟 $100 STRAIGHT-A BONUS ACHIEVED!")
    if missing_count > 0: st.error(f"🛑 PAYOUT LOCKED: {missing_count} missing assignment(s) detected.")

if not history_df.empty:
    st.divider()
    st.header("📈 Grade Trends")
    st.line_chart(history_df.groupby('ReportDate')['score'].mean())
