# 📊 Daily Market Dashboard — Automated Email Report

A fully automated system that generates a professional PDF market report every day at **7:00 AM SGT** and emails it to you via [Resend](https://resend.com). Runs free on GitHub Actions.

## What's In The Report

| Section | Contents |
|---------|----------|
| **Equity & Sector ETFs** | SPY, QQQ, IGV, XLK, XLF, XLY, XLC, XLI, XLB, XLE, XLP, XLV, XLU, XLRE |
| **Crypto** | BTC-USD, ETH-USD |
| **Bond Yields** | US 2Y, 10Y, 30Y, Japan 10Y — current yield + 1D/1W/1M bps changes |
| **Precious Metals** | Gold & Silver spot prices with 24hr moves |

Returns shown: **1D, 1W, 1M, 3M, 6M, 1Y, 3Y** — color-coded green/red.

---

## ⚡ Quick Setup (15 minutes)

### Step 1: Create a Resend Account & API Key

1. Go to [resend.com](https://resend.com) and sign up (free)
2. **Option A — Quick test (no domain needed):**
   - Resend gives you a free test sender: `onboarding@resend.dev`
   - You can only send to **your own email** (the one you signed up with)
   - Good for testing, but limited to one recipient
3. **Option B — Custom domain (recommended for daily use):**
   - Go to [resend.com/domains](https://resend.com/domains) → **Add Domain**
   - Add a domain you own (e.g., `yourdomain.com`)
   - Add the DNS records Resend provides (MX, TXT, DKIM)
   - Wait for verification (~5 minutes)
   - Then you can send from e.g. `reports@yourdomain.com` to anyone
4. Go to [resend.com/api-keys](https://resend.com/api-keys) → **Create API Key**
5. Copy the key (starts with `re_`)

### Step 2: Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `market-report-bot` (private recommended)
3. Upload all files from this project:
   ```
   market-report-bot/
   ├── .github/workflows/daily_report.yml
   ├── generate_report.py
   ├── requirements.txt
   └── README.md
   ```

### Step 3: Add GitHub Secrets

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** and add:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `RESEND_API_KEY` | Your Resend API key | `re_abc123xyz...` |
| `EMAIL_SENDER` | Verified sender address | `Market Dashboard <reports@yourdomain.com>` |
| `EMAIL_RECIPIENT` | Where to receive the report | `you@gmail.com` |

> **If using Resend's free test sender**, set `EMAIL_SENDER` to `onboarding@resend.dev` and `EMAIL_RECIPIENT` to the email you signed up with.

### Step 4: Test It

1. Go to your repo → **Actions** tab
2. Click **"Daily Market Report"** on the left
3. Click **"Run workflow"** → **"Run workflow"** (green button)
4. Wait ~2 minutes. Check your email!

### Step 5: You're Done! 🎉

The report will now auto-send every weekday at 7:00 AM SGT.

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

### Send to multiple recipients
```python
# In generate_report.py, the "to" field already accepts a list:
"to": ["you@gmail.com", "friend@gmail.com"]
```
Or set `EMAIL_RECIPIENT` to comma-separated addresses and update the code:
```python
"to": os.environ.get("EMAIL_RECIPIENT").split(",")
```

---

## Why Resend Instead of Gmail?

| | Gmail App Password | Resend API |
|---|---|---|
| **Security** | Exposes your Gmail credentials | Isolated API key, no access to your inbox |
| **Revocation** | Must manage in Google account | One-click revoke in Resend dashboard |
| **Deliverability** | Can hit spam filters | Built-in DKIM/SPF, designed for transactional email |
| **Rate limits** | 500/day, Google may throttle | 100/day free tier (more than enough) |
| **Setup** | Requires 2FA + App Password | Sign up → get API key → done |

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

- **Yahoo Finance** is used as the data source via `yfinance`. It's free but occasionally has gaps.
- **Japan 10-Year yield** doesn't have a reliable Yahoo Finance ticker. The report notes this; consider a secondary API for production.
- **GitHub Actions free tier** gives 2,000 min/month for private repos. This uses ~44 min/month — well within limits.
- The PDF is also saved as a **GitHub Actions artifact** for 30 days as a backup.
- **Resend free tier** allows 100 emails/day and 3,000/month — more than enough for a daily report.

## 📜 License

MIT — use freely.
