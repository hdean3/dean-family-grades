# Dean Family Grades TV — Railway Deployment

Deploys the TV dashboard at a permanent URL.
Grades auto-update: GitHub Actions commits grades.json → Railway redeploys → TVs refresh.

## One-Time Setup

### 1. New Railway project (separate from SurveySlayer)
- Railway dashboard → New Project → Deploy from GitHub
- Select: `hdean3/dean-family-grades`
- Railway auto-reads the `Procfile`

### 2. No environment variables needed
The TV server reads `data/grades.json` directly from the repo.

### 3. Get your TV URL
- Railway → service → Settings → Domains
- Your TV URL: `https://your-url.up.railway.app/tv`

### 4. Bookmark on each TV
| TV | Browser | Steps |
|----|---------|-------|
| Insignia FireTV | Silk Browser | Open URL → ☆ Bookmark → set as homepage |
| LG OLED webOS | Built-in browser | Open URL → Bookmark |
| Nvidia Shield TV | Chrome | Open URL → ⋮ → Add to bookmarks |
| Apple TV | AirPlay from iPhone | Open URL on iPhone → AirPlay → your Apple TV |

### Auto-refresh
The TV page auto-refreshes grades every 5 minutes.
Grades update when Ben's school emails arrive (GitHub Actions runs fetch_grades.py).

## Railway CLI redeploy
```bash
cd ~/Projects/dean-family-grades
railway up
```

## Cost
- Minimal traffic (only family TVs) → well within $5/month free credit
- Can share the Railway project with SurveySlayer to stay under 1 service (free tier limit)
