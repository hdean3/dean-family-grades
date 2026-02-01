# 🎓 Automated Student Reward Dashboard
Track grades automatically and simulate financial rewards based on academic performance.

## 🚀 Features
- **Logic App Sync**: Syncs grades from automated school emails (Gmail) to Azure Storage.
- **Privacy First**: All names and payout amounts are hidden via Environment Variables.
- **Weekly Progress**: Metrics show how performance has changed since the last email.

## 🛠️ Setup
1. **Container App**: Deploy this image to Azure.
2. **Environment Variables**:
   - `STUDENT_NAME`: Your student's name.
   - `RATE_APLUS` ... `RATE_BMINUS`: Payout amounts.
   - `AZURE_STORAGE_CONNECTION_STRING`: Your storage access key.
3. **Automation**: Point an Azure Logic App to your student's grade email. Save the JSON output as `grades_@{utcNow()}.json` in your blob container.
