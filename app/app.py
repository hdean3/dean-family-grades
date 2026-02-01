import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

# --- PRIVACY & CONFIGURATION LAYER ---
# These are pulled from Azure Environment Variables for public safety
STUDENT_NAME = os.getenv("STUDENT_NAME", "Student") 
RATE_APLUS = float(os.getenv("RATE_APLUS", 150))
RATE_A = float(os.getenv("RATE_A", 125))
RATE_AMINUS = float(os.getenv("RATE_AMINUS", 100))
RATE_BPLUS = float(os.getenv("RATE_BPLUS", 75))
RATE_B = float(os.getenv("RATE_B", 50))
RATE_BMINUS = float(os.getenv("RATE_BMINUS", 25))

rates = {
    "A+": RATE_APLUS, "A": RATE_A, "A-": RATE_AMINUS, 
    "B+": RATE_BPLUS, "B": RATE_B, "B-": RATE_BMINUS
}

def get_history_and_summary():
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client("dean-family-grades")
    
    historical_data = []
    blobs = sorted(container_client.list_blobs(), key=lambda x: x.name)
    
    for blob in blobs:
        if blob.name.startswith("grades_") and blob.name.endswith(".json"):
            stream = container_client.download_blob(blob.name).readall()
            df = pd.read_json(io.BytesIO(stream))
            date_str = blob.name.split('_')[1].replace('.json', '')
            df['Date'] = pd.to_datetime(date_str)
            historical_data.append(df)
            
    if len(historical_data) >= 2:
        # Weekly Summary Logic
        latest = historical_data[-1]['grade_numeric'].mean()
        previous = historical_data[-2]['grade_numeric'].mean()
        delta = latest - previous
        st.subheader("📊 Weekly Progress Summary")
        st.metric("Academic Performance", f"{latest:.1f}%", delta=f"{delta:.1f}%")

    return pd.concat(historical_data) if historical_data else pd.DataFrame()

st.set_page_config(page_title=f"{STUDENT_NAME}: Rewards", layout="wide")
st.title(f"🎓 {STUDENT_NAME}: Semester Rewards")

# --- CURRENT DATA (Will be fed by your Logic App) ---
current_data = {
    'Aerospace Science I': 99,
    'US & VA History A': 93,
    'Economics': 83,
    'English 11A': 80,
    'Data Science': 77,
    'Env. Science': 76
}
missing_assignments = 1 # Logic App will update this

# --- THE PAYOUT TIERS ---
# We can refine these once Claudia gives the final word
rates = {"A+": 150, "A": 125, "A-": 100, "B+": 75, "B": 50, "B-": 25}

def get_payout(score):
    if score >= 97: return rates["A+"]
    if score >= 93: return rates["A"]
    if score >= 90: return rates["A-"]
    if score >= 87: return rates["B+"]
    if score >= 83: return rates["B"]
    if score >= 80: return rates["B-"]
    return 0

# --- CALCULATIONS ---
current_total = sum(get_payout(s) for s in current_data.values())
max_payout = len(current_data) * rates["A+"]

# --- SIDEBAR: MOTIVATION SLIDERS ---
st.sidebar.header("🚀 Motivation Simulator")
simulated_grades = {}
for subject, score in current_data.items():
    simulated_grades[subject] = st.sidebar.slider(f"{subject}", 60, 100, score)
sim_total = sum(get_payout(s) for s in simulated_grades.values())

# --- TOP METRICS ROW ---
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Max Potential", f"${max_payout:.2f}", help="What you get for all A+ grades")
with m2:
    if missing_assignments > 0:
        st.metric("Current Earned", "$0.00", delta=f"- ${current_total} Locked", delta_color="inverse")
    else:
        st.metric("Current Earned", f"${current_total:.2f}")
with m3:
    st.metric("Simulated Reward", f"${sim_total:.2f}", delta=f"${sim_total - current_total:.2f}")

# --- LOCK ALERT ---
if missing_assignments > 0:
    st.error(f"🛑 PAYOUT IS LOCKED. You have {missing_assignments} missing assignment in History. Turn it in to unlock your ${current_total}!")

st.divider()
st.write("### How to increase your payout:")
st.info("Move the sliders in the sidebar to see how much more you earn for every grade bump!")

history_df = get_history_and_summary()
if not history_df.empty:
    st.header("📈 Performance Over Time")
    st.line_chart(history_df.set_index('Date')['grade_numeric'])
