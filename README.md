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

## 📺 TV Splash Screen Backlog (added 2026-03-01)

Goal: Display Ben's current grades as an ambient dashboard on the living room TVs.

| Platform | Device | Approach | Effort |
|----------|--------|----------|--------|
| Fire OS | Insignia FireTV | Silk Browser bookmark → grades-tv.html (GitHub Pages) | Low |
| Fire OS | Insignia FireTV | Amazon Appstore app via Fire TV Web App Starter Kit (FWAK) | Medium |
| webOS | LG OLED | Built-in browser bookmark → grades-tv.html | Low |
| tvOS | Apple TV | AirPlay mirror from iPhone | Low (manual) |
| tvOS | Apple TV | Native tvOS app | High ($99 Dev acct) |
| Android TV | Nvidia Shield TV | Chrome browser or custom launcher | Low |

**Milestones:**
- [ ] TV-M1: `grades-tv.html` — 10-foot UI page (large font, dark bg, auto-refresh 5 min), served via GitHub Pages
- [ ] TV-M2: Bookmark on Insignia FireTV Silk Browser + LG browser
- [ ] TV-M3: Fire TV Web App (FWAK) → Amazon Appstore free submission
- [ ] TV-M4: Explore Nvidia Shield / Android TV launcher widget
- [ ] TV-M5: Apple TV via AirPlay automation (Shortcut on iPad/iPhone)
