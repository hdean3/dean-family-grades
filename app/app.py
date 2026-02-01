import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import os

def render_history():
    st.header("📈 Grade Performance Over Time")
    
    # Connect to storage
    connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client("dean-family-grades")
    
    historical_data = []
    blobs = container_client.list_blobs()
    
    for blob in blobs:
        if blob.name.startswith("grades_") and blob.name.endswith(".json"):
            # Download and parse each week's file
            stream = container_client.download_blob(blob.name).readall()
            df = pd.read_json(io.BytesIO(stream))
            
            # Extract date from filename: grades_2026-02-01.json
            date_str = blob.name.split('_')[1].replace('.json', '')
            df['Date'] = pd.to_datetime(date_str)
            historical_data.append(df)
            
    if historical_data:
        full_history = pd.concat(historical_data)
        # Create a chart showing GPA or average grade value over time
        st.line_chart(full_history.set_index('Date')['grade_numeric'])
    else:
        st.info("No history yet! Tracking will start with your next Grade Update email.")

# --- PRIVACY LAYER (For your Backlog) ---
# We use environment variables so you can make this repo Public later
STUDENT_NAME = os.getenv("STUDENT_NAME", "Ben Dean") 

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

render_history()
