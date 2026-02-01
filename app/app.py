import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- 1. CONFIGURATION ---
STUDENT_NAME = os.getenv("STUDENT_NAME", "Student") 
rates = {
    "A+": float(os.getenv("RATE_APLUS", 150.0)),
    "A": float(os.getenv("RATE_A", 125.0)),
    "A-": float(os.getenv("RATE_AMINUS", 100.0)),
    "B+": float(os.getenv("RATE_BPLUS", 75.0)),
    "B": float(os.getenv("RATE_B", 50.0)),
    "B-": float(os.getenv("RATE_BMINUS", 25.0))
}

# School Colors
st.markdown(f"<style>.stMetric {{ border-left: 5px solid #800000; }} h1 {{ color: #000080; }}</style>", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        st.error("DEBUG: AZURE_STORAGE_CONNECTION_STRING is missing in Environment Variables!")
        return None, pd.DataFrame()
    
    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        container = client.get_container_client("dean-family-grades")
        blobs = list(container.list_blobs())
        
        if not blobs:
            st.warning("DEBUG: Connection successful, but container 'dean-family-grades' is EMPTY.")
            return None, pd.DataFrame()

        historical_data = []
        latest_df = None
        for blob in sorted(blobs, key=lambda x: x.name):
            if "grades" in blob.name and blob.name.endswith(".json"):
                data = container.download_blob(blob.name).readall()
                df = pd.read_json(io.BytesIO(data))
                historical_data.append(df)
                latest_df = df 
        return latest_df, pd.concat(historical_data) if historical_data else pd.DataFrame()
    except Exception as e:
        st.error(f"DEBUG: Storage Connection Failed: {str(e)}")
        return None, pd.DataFrame()

# --- 3. UI RENDERING ---
st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
current_df, history_df = load_data()

st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

if current_df is not None:
    def get_payout(score):
        if score >= 97: return rates["A+"]
        if score >= 93: return rates["A"]
        if score >= 90: return rates["A-"]
        if score >= 87: return rates["B+"]
        if score >= 83: return rates["B"]
        if score >= 80: return rates["B-"]
        return 0

    current_df['Earnings'] = current_df['score'].apply(get_payout)
    base_total = current_df['Earnings'].sum()
    all_as = all(score >= 90 for score in current_df['score'])
    bonus = 100.0 if all_as else 0.0
    current_total = base_total + bonus
    
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Max Potential", "$1,000.00")
    with m2: st.metric("Earned To Date", f"${current_total:.2f}")
    with m3: st.metric("GPA", f"{current_df['score'].mean():.1f}%")

    st.subheader("💰 breakdown")
    st.dataframe(current_df[['subject', 'score', 'Earnings']], use_container_width=True)
