# 🎓 Student Grade Reward Dashboard
A private, automated dashboard for tracking student grades and simulating financial rewards based on academic performance.

## 🚀 Features
- **Automated Sync**: Uses Azure Logic Apps to parse automated school grade emails (Gmail).
- **Motivation Simulator**: Sidebar sliders allow students to see how much their payout increases with every grade bump.
- **Privacy First**: All personal names and payout amounts are handled via Environment Variables.

## 🛠️ Setup
1. **Azure Container App**: Deploy this repo as a container.
2. **Environment Variables**:
   - `STUDENT_NAME`: Display name for the dashboard.
   - `RATE_APLUS`: Dollar amount for an A+ (e.g., 150).
   - `AZURE_STORAGE_CONNECTION_STRING`: Connection to your Azure Blob Storage.
3. **Automation**: Link a Logic App to your Gmail. Send an email with subject "Grade Update" to trigger a sync.
