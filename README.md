# 🎓 Student Academic Reward Tracker
Automate grade tracking and motivate students with real-time financial reward simulations.

## 🚀 How it Works
1. **Logic App**: Senses incoming school emails, parses grades, and saves them to Azure Blob Storage.
2. **Container App**: A Streamlit dashboard that calculates rewards based on customizable tiers.
3. **Privacy**: No student names are stored in the code. All configuration is done via Environment Variables.

## 🛠️ Configuration
Set these Environment Variables in your Azure Container App:
- `STUDENT_NAME`: (e.g., "Ben Dean")
- `RATE_APLUS`: (e.g., 150)
- `AZURE_STORAGE_CONNECTION_STRING`: Your storage access key.
