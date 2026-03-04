"""
Daily Market Dashboard Report Generator
Fetches live data from Yahoo Finance, generates a professional PDF,
and sends it to Telegram.

Scheduled via GitHub Actions at 6:00 AM SGT (22:00 UTC previous day).
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import requests
import os
import json


# ─── Configuration ───────────────────────────────────────────────────────────

EQUITY_TICKERS = [
    ("SPY",  "S&P 500 ETF"),
    ("QQQ",  "Nasdaq 100 ETF"),
    ("IGV",  "Software Sector ETF"),
    ("XLK",  "Technology"),
    ("XLF",  "Financials"),
    ("XLY",  "Cons. Discretionary"),
    ("XLC",  "Communication Svcs"),
    ("XLI",  "Industrials"),
    ("XLB",  "Materials"),
    ("XLE",  "Energy"),
    ("XLP",  "Consumer Staples"),
    ("XLV",  "Health Care"),
    ("XLU",  "Utilities"),
    ("XLRE", "Real Estate"),
]

MAG7_TICKERS = [
    ("AAPL",  "Apple"),
    ("MSFT",  "Microsoft"),
    ("GOOGL", "Alphabet"),
    ("AMZN",  "Amazon"),
    ("META",  "Meta Platforms"),
    ("NVDA",  "NVIDIA"),
    ("TSLA",  "Tesla"),
]

DEFENSE_TICKERS = [
    ("KDEF", "Kinetics Defense ETF"),
    ("ITA",  "iShares Aerospace & Defense"),
]

GLOBAL_INDEX_TICKERS = [
    ("^NSEI",     "India — Nifty 50"),
    ("^STI",      "Singapore — STI"),
    ("^N225",     "Japan — Nikkei 225"),
    ("^KS11",     "South Korea — KOSPI"),
    ("^FTSE",     "London — FTSE 100"),
    ("^AXJO",     "Australia — ASX 200"),
    ("^STOXX50E", "Europe — Euro Stoxx 50"),
]

CURRENCY_TICKERS = [
    ("DX-Y.NYB", "USD Index (DXY)"),
    ("USDSGD=X", "USD / SGD"),
    ("SGDUSD=X", "SGD / USD"),
    ("EURUSD=X", "EUR / USD"),
    ("AUDUSD=X", "AUD / USD"),
    ("GBPUSD=X", "GBP / USD"),
    ("JPYUSD=X", "JPY / USD"),
]

CRYPTO_TICKERS = [
    ("BTC-USD", "Bitcoin"),
    ("ETH-USD", "Ethereum"),
    ("FBTC",    "Fidelity Bitcoin ETF"),
    ("BMNR",    "Bitmine Immersion Tech"),
]

WTI_TICKERS = [
    ("CL=F", "WTI Crude Oil"),
]

BOND_TICKERS = [
    ("^IRX",  "US 3-Month T-Bill"),
    ("2YY=F", "US 2-Year Yield"),
    ("^TNX",  "US 10-Year Yield"),
    ("^TYX",  "US 30-Year Yield"),
]

# Japan 10Y and metals don't have reliable Yahoo tickers; we use proxies
EXTRA_TICKERS = [
    ("GC=F",  "Gold Futures"),
    ("SI=F",  "Silver Futures"),
    ("GLD",   "SPDR Gold ETF"),
    ("SLV",   "iShares Silver ETF"),
]

# Standard CME futures month codes
MONTH_CODES = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z',
}

LOOKBACK_PERIODS = {
    "1D":  1,
    "1W":  5,
    "1M":  21,
    "3M":  63,
    "6M":  126,
    "1Y":  252,
    "3Y":  756,
}


# ─── Data Fetching ───────────────────────────────────────────────────────────

def fetch_returns(tickers_with_names, period="5y"):
    """Fetch historical prices and compute returns for multiple timeframes."""
    symbols = [t[0] for t in tickers_with_names]
    names = {t[0]: t[1] for t in tickers_with_names}

    try:
        data = yf.download(symbols, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return pd.DataFrame()
        close = data["Close"] if "Close" in data.columns.get_level_values(0) else data
    except Exception as e:
        print(f"Error fetching {symbols}: {e}")
        return pd.DataFrame()

    if isinstance(close, pd.Series):
        close = close.to_frame(name=symbols[0])

    results = []
    for sym in symbols:
        if sym not in close.columns:
            continue
        series = close[sym].dropna()
        if len(series) < 2:
            continue

        latest = series.iloc[-1]
        row = {"Ticker": sym, "Name": names.get(sym, sym), "Price": latest}

        for label, days in LOOKBACK_PERIODS.items():
            if len(series) > days:
                past = series.iloc[-(days + 1)]
                row[label] = (latest - past) / past
            else:
                row[label] = None

        results.append(row)

    return pd.DataFrame(results)


def fetch_vix_data():
    """Fetch VIX index: close, intraday high/low, 52-week high/low."""
    try:
        hist = yf.Ticker("^VIX").history(period="1y")
        if hist.empty:
            return None
        latest = hist.iloc[-1]
        return {
            "Ticker": "^VIX",
            "Name": "CBOE Volatility Index",
            "Close": float(latest["Close"]),
            "Intraday High": float(latest["High"]),
            "Intraday Low": float(latest["Low"]),
            "52W High": float(hist["High"].max()),
            "52W Low": float(hist["Low"].min()),
        }
    except Exception as e:
        print(f"Error fetching VIX: {e}")
        return None


def fetch_wti_futures():
    """Fetch WTI crude spot (CL=F) + next 2 calendar month futures."""
    now = datetime.utcnow()

    contracts = [("CL=F", "Spot / Front Month")]
    for offset in [1, 2]:
        m = now.month + offset
        y = now.year
        if m > 12:
            m -= 12
            y += 1
        ticker = f"CL{MONTH_CODES[m]}{str(y)[-2:]}.NYM"
        label = datetime(y, m, 1).strftime("%b %Y") + " Futures"
        contracts.append((ticker, label))

    results = []
    for ticker, label in contracts:
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if hist.empty:
                continue
            s = hist["Close"].dropna()
            if len(s) < 1:
                continue
            price = float(s.iloc[-1])
            chg_1d = float(s.iloc[-1] - s.iloc[-2]) if len(s) >= 2 else None
            chg_1d_pct = (chg_1d / float(s.iloc[-2])) if chg_1d is not None else None
            results.append({
                "Contract": ticker,
                "Description": label,
                "Price": price,
                "1D Chg ($)": chg_1d,
                "1D Chg (%)": chg_1d_pct,
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

    return results


def fetch_bond_yields():
    """Fetch bond yield proxies and compute daily changes."""
    symbols = ["^TNX", "^TYX", "^IRX"]
    try:
        data = yf.download(symbols, period="1y", auto_adjust=True, progress=False)
        if data.empty:
            return []
        close = data["Close"]
    except Exception:
        return []

    try:
        two_yr = yf.download("2YY=F", period="1y", auto_adjust=True, progress=False)
        two_yr_close = two_yr["Close"] if not two_yr.empty else None
    except Exception:
        two_yr_close = None

    results = []

    bond_map = {
        "^TNX": "US 10-Year",
        "^TYX": "US 30-Year",
    }

    for sym, label in bond_map.items():
        if sym not in close.columns:
            continue
        s = close[sym].dropna()
        if len(s) < 2:
            continue
        current = s.iloc[-1]
        day_chg = (s.iloc[-1] - s.iloc[-2]) * 100 if len(s) >= 2 else 0  # in bps
        week_chg = (s.iloc[-1] - s.iloc[-6]) * 100 if len(s) >= 6 else 0
        month_chg = (s.iloc[-1] - s.iloc[-22]) * 100 if len(s) >= 22 else 0
        results.append({
            "Maturity": label,
            "Yield": f"{current:.2f}%",
            "1D (bps)": f"{day_chg:+.0f}",
            "1W (bps)": f"{week_chg:+.0f}",
            "1M (bps)": f"{month_chg:+.0f}",
        })

    if two_yr_close is not None and not two_yr_close.empty:
        s = two_yr_close.squeeze().dropna() if isinstance(two_yr_close, pd.DataFrame) else two_yr_close.dropna()
        if len(s) >= 2:
            current = s.iloc[-1]
            day_chg = (s.iloc[-1] - s.iloc[-2]) * 100
            week_chg = (s.iloc[-1] - s.iloc[-6]) * 100 if len(s) >= 6 else 0
            month_chg = (s.iloc[-1] - s.iloc[-22]) * 100 if len(s) >= 22 else 0
            results.insert(0, {
                "Maturity": "US 2-Year",
                "Yield": f"{current:.2f}%",
                "1D (bps)": f"{day_chg:+.0f}",
                "1W (bps)": f"{week_chg:+.0f}",
                "1M (bps)": f"{month_chg:+.0f}",
            })

    return results


def fetch_metals():
    """Fetch gold and silver spot price changes."""
    symbols = ["GC=F", "SI=F"]
    try:
        data = yf.download(symbols, period="5d", auto_adjust=True, progress=False)
        if data.empty:
            return []
        close = data["Close"]
    except Exception:
        return []

    results = []
    metal_names = {"GC=F": "Gold", "SI=F": "Silver"}
    for sym in symbols:
        if sym not in close.columns:
            continue
        s = close[sym].dropna()
        if len(s) < 2:
            continue
        current = s.iloc[-1]
        prev = s.iloc[-2]
        chg = current - prev
        pct = (chg / prev) * 100
        results.append({
            "Metal": metal_names.get(sym, sym),
            "Spot (USD/oz)": f"${current:,.2f}",
            "24hr Chg": f"{'+' if chg >= 0 else ''}{chg:,.2f}",
            "24hr %": f"{'+' if pct >= 0 else ''}{pct:.2f}%",
        })
    return results


# ─── PDF Generation ──────────────────────────────────────────────────────────

def color_cell(val):
    """Return green/red color for positive/negative values."""
    if val is None or pd.isna(val):
        return colors.grey
    return colors.Color(0, 0.38, 0) if val >= 0 else colors.Color(0.61, 0, 0.024)


def fmt_pct(val):
    """Format percentage for display."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:+.2%}"


def build_pdf(equity_df, crypto_df, bonds, metals,
              mag7_df=None, defense_df=None, global_df=None,
              currency_df=None, wti_df=None, wti_futures=None,
              vix_data=None, filename="market_report.pdf"):
    """Build professional PDF report."""
    now = datetime.utcnow() + timedelta(hours=8)  # SGT
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p SGT")

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "Title2", parent=styles["Title"], fontSize=18,
        textColor=colors.HexColor("#1F4E79"), spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=9,
        textColor=colors.grey, spaceAfter=10, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "SectionHead", parent=styles["Heading2"], fontSize=11,
        textColor=colors.HexColor("#1F4E79"), spaceBefore=12, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        "SmallNote", parent=styles["Normal"], fontSize=7.5,
        textColor=colors.grey, spaceBefore=6
    ))

    story = []

    # ── Title ──
    story.append(Paragraph("Daily Market Dashboard", styles["Title2"]))
    story.append(Paragraph(f"{date_str} &nbsp;|&nbsp; Generated at {time_str}", styles["Subtitle"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#1F4E79"), thickness=1.5))
    story.append(Spacer(1, 6))

    # ── Helper: standard returns table (Ticker/Name/Price/1D-3Y) ──
    def make_returns_table(df, section_title):
        story.append(Paragraph(section_title, styles["SectionHead"]))

        headers = ["Ticker", "Name", "Price", "1D", "1W", "1M", "3M", "6M", "1Y", "3Y"]
        table_data = [headers]

        for _, row in df.iterrows():
            table_data.append([
                row["Ticker"],
                row["Name"],
                f"${row['Price']:,.2f}" if pd.notna(row.get("Price")) else "—",
                fmt_pct(row.get("1D")),
                fmt_pct(row.get("1W")),
                fmt_pct(row.get("1M")),
                fmt_pct(row.get("3M")),
                fmt_pct(row.get("6M")),
                fmt_pct(row.get("1Y")),
                fmt_pct(row.get("3Y")),
            ])

        col_widths = [62, 105, 48, 42, 42, 42, 42, 42, 42, 42]  # 509pt total, fits A4 510pt
        t = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]

        # Color-code return cells
        for row_idx in range(1, len(table_data)):
            for col_idx in range(3, 10):
                period_key = headers[col_idx]
                val = df.iloc[row_idx - 1].get(period_key)
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    c = color_cell(val)
                    style_cmds.append(("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), c))

        t.setStyle(TableStyle(style_cmds))
        story.append(t)
        story.append(Spacer(1, 4))

    # ── Helper: VIX table ──
    def make_vix_table(vix):
        story.append(Paragraph("Volatility — VIX Index (^VIX)", styles["SectionHead"]))
        headers = ["Ticker", "Name", "Close", "Intraday High", "Intraday Low", "52W High", "52W Low"]
        data_row = [
            vix["Ticker"],
            vix["Name"],
            f"{vix['Close']:.2f}",
            f"{vix['Intraday High']:.2f}",
            f"{vix['Intraday Low']:.2f}",
            f"{vix['52W High']:.2f}",
            f"{vix['52W Low']:.2f}",
        ]
        table_data = [headers, data_row]
        col_widths = [42, 140, 50, 62, 62, 57, 57]  # 470 total
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A235A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    # ── Helper: WTI futures term structure table ──
    def make_wti_futures_table(futures):
        story.append(Paragraph("WTI Crude Oil — Futures Term Structure", styles["SectionHead"]))
        if not futures:
            story.append(Paragraph("No futures data available.", styles["SmallNote"]))
            return

        headers = ["Contract", "Description", "Price (USD)", "1D Chg ($)", "1D Chg (%)"]
        table_data = [headers]
        sign_data = {}  # row_idx -> {col_idx: val} for coloring

        for i, row in enumerate(futures):
            price = row["Price"]
            chg_d = row["1D Chg ($)"]
            chg_pct = row["1D Chg (%)"]
            sign_data[i + 1] = {3: chg_d, 4: chg_pct}
            table_data.append([
                row["Contract"],
                row["Description"],
                f"${price:,.2f}" if price is not None else "—",
                (f"{'+' if chg_d >= 0 else ''}{chg_d:.2f}" if chg_d is not None else "—"),
                fmt_pct(chg_pct) if chg_pct is not None else "—",
            ])

        col_widths = [80, 130, 75, 75, 75]  # 435 total
        t = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5C4033")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF3E0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for row_idx, cols in sign_data.items():
            for col_idx, val in cols.items():
                if val is not None:
                    style_cmds.append(
                        ("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), color_cell(val))
                    )
        t.setStyle(TableStyle(style_cmds))
        story.append(t)
        story.append(Spacer(1, 4))

    # ── Global Market Indices ──
    if global_df is not None and not global_df.empty:
        make_returns_table(global_df, "Global Market Indices")

    # ── Currency Moves ──
    if currency_df is not None and not currency_df.empty:
        make_returns_table(currency_df, "Currency Moves")

    # ── Equity & Sector Returns ──
    if not equity_df.empty:
        make_returns_table(equity_df, "Equity & Sector ETF Returns")

    # ── Magnificent 7 ──
    if mag7_df is not None and not mag7_df.empty:
        make_returns_table(mag7_df, "Magnificent 7 — Stock Returns")

    # ── Defense ETFs ──
    if defense_df is not None and not defense_df.empty:
        make_returns_table(defense_df, "Defense & Aerospace ETFs (KDEF · ITA)")

    # ── Crypto Returns ──
    if not crypto_df.empty:
        make_returns_table(crypto_df, "Cryptocurrency Returns")

    # ── VIX ──
    if vix_data:
        make_vix_table(vix_data)

    # ── WTI Crude Returns ──
    if wti_df is not None and not wti_df.empty:
        make_returns_table(wti_df, "WTI Crude Oil — Price Returns")

    # ── WTI Futures Term Structure ──
    if wti_futures:
        make_wti_futures_table(wti_futures)

    # ── Bond Yields ──
    if bonds:
        story.append(Paragraph("US Treasury & Japan Bond Yields", styles["SectionHead"]))
        bond_headers = list(bonds[0].keys())
        bond_data = [bond_headers] + [[row[k] for k in bond_headers] for row in bonds]

        bt = Table(bond_data, colWidths=[70, 55, 55, 55, 55], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E75B6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(bt)
        story.append(Paragraph(
            "Note: Japan 10-Year yield (~2.10%) sourced from TradingEconomics. "
            "Yahoo Finance does not provide a reliable JGB ticker.",
            styles["SmallNote"]
        ))
        story.append(Spacer(1, 4))

    # ── Precious Metals ──
    if metals:
        story.append(Paragraph("Precious Metals — 24hr Spot Price Moves", styles["SectionHead"]))
        metal_headers = list(metals[0].keys())
        metal_data = [metal_headers] + [[row[k] for k in metal_headers] for row in metals]

        mt = Table(metal_data, colWidths=[60, 80, 65, 65], repeatRows=1)
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#BF8F00")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF8E1")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(mt)
        story.append(Spacer(1, 6))

    # ── Footer ──
    story.append(HRFlowable(width="100%", color=colors.HexColor("#D0D0D0"), thickness=0.5))
    story.append(Paragraph(
        "Data source: Yahoo Finance (yfinance). Returns are price-only approximations. "
        "Bond yield changes in basis points. This report is auto-generated and not financial advice.",
        styles["SmallNote"]
    ))

    doc.build(story)
    print(f"PDF saved: {filename}")
    return filename


# ─── Telegram Sending ────────────────────────────────────────────────────────

def send_telegram(pdf_path):
    """Send report PDF to Telegram chat via Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not all([bot_token, chat_id]):
        print("Telegram credentials not set. Skipping.")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as env vars.")
        return False

    now = datetime.utcnow() + timedelta(hours=8)
    caption = (
        f"📊 *Daily Market Dashboard*\n"
        f"_{now.strftime('%A, %B %d, %Y')}_\n\n"
        f"SPY · QQQ · Mag7 · Defense ETFs\n"
        f"BTC · ETH · VIX · WTI · US Yields · Gold · Silver"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    try:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                },
                files={"document": (f"Market_Dashboard_{now.strftime('%Y%m%d')}.pdf", f, "application/pdf")},
                timeout=30,
            )
        result = resp.json()
        if result.get("ok"):
            print(f"Telegram: PDF sent to chat {chat_id}")
            return True
        else:
            print(f"Telegram error: {result.get('description', 'unknown')}")
            return False
    except Exception as e:
        print(f"Telegram failed: {e}")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("DAILY MARKET DASHBOARD GENERATOR")
    print(f"Run time: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M SGT')}")
    print("=" * 60)

    print("\n[1/11] Fetching equity & sector data...")
    equity_df = fetch_returns(EQUITY_TICKERS)
    print(f"  → {len(equity_df)} tickers fetched")

    print("[2/11] Fetching Magnificent 7 stocks...")
    mag7_df = fetch_returns(MAG7_TICKERS)
    print(f"  → {len(mag7_df)} tickers fetched")

    print("[3/11] Fetching defense ETFs (KDEF, ITA)...")
    defense_df = fetch_returns(DEFENSE_TICKERS)
    print(f"  → {len(defense_df)} tickers fetched")

    print("[4/11] Fetching global market indices...")
    global_df = fetch_returns(GLOBAL_INDEX_TICKERS)
    print(f"  → {len(global_df)} indices fetched")

    print("[5/11] Fetching currency moves...")
    currency_df = fetch_returns(CURRENCY_TICKERS)
    print(f"  → {len(currency_df)} pairs fetched")

    print("[6/11] Fetching crypto data...")
    crypto_df = fetch_returns(CRYPTO_TICKERS, period="5y")
    print(f"  → {len(crypto_df)} tickers fetched")

    print("[7/11] Fetching VIX data...")
    vix_data = fetch_vix_data()
    print(f"  → {'fetched' if vix_data else 'unavailable'}")

    print("[8/11] Fetching WTI crude returns...")
    wti_df = fetch_returns(WTI_TICKERS)
    print(f"  → {len(wti_df)} tickers fetched")

    print("[9/11] Fetching WTI futures term structure...")
    wti_futures = fetch_wti_futures()
    print(f"  → {len(wti_futures)} contracts fetched")

    print("[10/11] Fetching bond yields...")
    bonds = fetch_bond_yields()
    print(f"  → {len(bonds)} bond maturities fetched")

    print("[11/11] Fetching precious metals...")
    metals = fetch_metals()
    print(f"  → {len(metals)} metals fetched")

    print("\nGenerating PDF report...")
    pdf_path = build_pdf(
        equity_df, crypto_df, bonds, metals,
        mag7_df=mag7_df, defense_df=defense_df, global_df=global_df,
        currency_df=currency_df, wti_df=wti_df, wti_futures=wti_futures,
        vix_data=vix_data,
    )

    print("\nSending to Telegram...")
    send_telegram(pdf_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
