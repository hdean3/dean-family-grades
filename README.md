# 🎓 Student Grade & Reward Dashboard
Automated Streamlit dashboard to track school grades and calculate financial rewards.

## 🚀 Key Features
- **Automatic Sync**: Integrates with Azure Logic Apps to parse automated school grade emails.
- **Privacy Controls**: All student names and payout amounts are handled via Environment Variables.
- **Progress Tracking**: Real-time charts showing academic trends week-over-week.

## 🛠️ Deployment Configuration
Deploy the container and set these Environment Variables in the Azure Portal:
- `STUDENT_NAME`: Display name (e.g., Ben Dean)
- `RATE_APLUS`: Reward for an A+ (e.g., 150)
- `AZURE_STORAGE_CONNECTION_STRING`: Your Azure Blob Storage connection string.
- `CONTAINER_NAME`: The blob container holding your JSON grade reports.
