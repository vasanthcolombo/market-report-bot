# 📊 Daily Market Dashboard — Automated Email Report

A fully automated system that generates a professional PDF market report every day at **7:00 AM SGT** and emails it to you. Runs free on GitHub Actions.

## What's In The Report

| Section | Contents |
|---------|----------|
| **Equity & Sector ETFs** | SPY, QQQ, IGV, XLK, XLF, XLY, XLC, XLI, XLB, XLE, XLP, XLV, XLU, XLRE |
| **Crypto** | BTC-USD, ETH-USD |
| **Bond Yields** | US 2Y, 10Y, 30Y — current yield + 1D/1W/1M basis point changes |
| **Precious Metals** | Gold & Silver spot prices with 24hr moves |

Returns shown: **1D, 1W, 1M, 3M, 6M, 1Y, 3Y** — color-coded green/red.

---

## ⚡ Quick Setup (15 minutes)

### Step 1: Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `market-report-bot` (private recommended)
3. Upload all files from this project, preserving the folder structure:
   ```
   market-report-bot/
   ├── .github/workflows/daily_report.yml
   ├── generate_report.py
   ├── requirements.txt
   └── README.md
   ```

### Step 2: Create a Gmail App Password

> You need a Gmail **App Password**, NOT your regular password.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already on
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Select **"Mail"** and **"Other"** → name it `Market Report Bot`
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 3: Add GitHub Secrets

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** and add these three:

| Secret Name | Value |
|-------------|-------|
| `EMAIL_SENDER` | Your Gmail address (e.g., `you@gmail.com`) |
| `EMAIL_PASSWORD` | The 16-char App Password from Step 2 |
| `EMAIL_RECIPIENT` | Where to receive the report (can be same or different email) |

### Step 4: Test It

1. Go to your repo → **Actions** tab
2. Click **"Daily Market Report"** on the left
3. Click **"Run workflow"** → **"Run workflow"** (green button)
4. Wait ~2 minutes. Check your email!

### Step 5: You're Done! 🎉

The report will now auto-send every day at 7:00 AM SGT (weekdays only).

---

## 🔧 Customization

### Change the schedule
Edit `.github/workflows/daily_report.yml`:
```yaml
# Examples:
- cron: '0 23 * * 0-4'    # 7:00 AM SGT, Mon–Fri
- cron: '30 22 * * *'      # 6:30 AM SGT, every day
- cron: '0 23 * * 0-6'     # 7:00 AM SGT, Mon–Sun
```

### Add/remove tickers
Edit the ticker lists at the top of `generate_report.py`:
```python
EQUITY_TICKERS = [
    ("SPY",  "S&P 500 ETF"),
    ("ARKK", "ARK Innovation ETF"),  # ← Add new ones here
    ...
]
```

### Change email provider (non-Gmail)
Edit the `send_email()` function in `generate_report.py`:
- **Outlook**: `smtp.office365.com`, port 587, use `starttls()`
- **Yahoo**: `smtp.mail.yahoo.com`, port 465
- **SendGrid**: `smtp.sendgrid.net`, port 587

### Send to multiple recipients
Set `EMAIL_RECIPIENT` to comma-separated addresses:
```
you@gmail.com,friend@gmail.com
```
Then update the code: `recipient = os.environ.get("EMAIL_RECIPIENT").split(",")`

---

## 📁 Project Structure

```
market-report-bot/
├── .github/
│   └── workflows/
│       └── daily_report.yml    # GitHub Actions cron schedule
├── generate_report.py          # Main script (fetch data → PDF → email)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## ⚠️ Notes

- **Yahoo Finance** is used as the data source. It's free but occasionally has gaps or delays.
- **Japan 10-Year yield** doesn't have a reliable Yahoo Finance ticker. The report includes a note about this; for production use, consider adding a secondary API (e.g., TradingEconomics API).
- **GitHub Actions free tier** gives you 2,000 minutes/month for private repos. This workflow uses ~2 min/run × 22 weekdays = ~44 min/month — well within limits.
- The PDF is also saved as a **GitHub Actions artifact** for 30 days as a backup.

## 📜 License

MIT — use freely.
