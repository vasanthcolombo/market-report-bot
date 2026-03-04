# Claude Context — Market Report Bot

## Project
- **Repo**: https://github.com/vasanthcolombo/market-report-bot
- **Purpose**: Automated daily market dashboard PDF emailed every weekday morning

## Schedule
- **Cron**: `0 22 * * 1-5` (22:00 UTC Mon–Fri = 6:00 AM SGT Tue–Sat)
- **Runner**: GitHub Actions (free tier)

## Email Delivery
- **Provider**: Resend (resend.com) — free tier, 100 emails/day
- **Secrets in GitHub**: `RESEND_API_KEY`, `EMAIL_SENDER`, `EMAIL_RECIPIENT`

## Report Contents
- **Equity & Sector ETFs**: SPY, QQQ, IGV, XLK, XLF, XLY, XLC, XLI, XLB, XLE, XLP, XLV, XLU, XLRE
- **Crypto**: BTC-USD, ETH-USD
- **Bond Yields**: US 2Y, 10Y, 30Y, Japan 10Y — current yield + 1D/1W/1M bps changes
- **Precious Metals**: Gold & Silver spot prices with 24hr moves
- **Return Periods**: 1D, 1W, 1M, 3M, 6M, 1Y, 3Y (color-coded green/red)

## Data Source
- Yahoo Finance via `yfinance` Python library
- Japan 10Y yield: no reliable Yahoo ticker — noted in report

## Tech Stack
- Python 3.12
- `yfinance`, `pandas`, `numpy`, `reportlab`, `resend`
- PDF output via ReportLab
- GitHub Actions for scheduling

## User Preferences
- **Location**: Singapore (SGT, UTC+8)
- **Format**: PDF attachment via email
- **Frequency**: Weekday mornings
